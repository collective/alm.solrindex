"""SolrIndex and SolrConnectionManager"""
import logging
import os
import transaction

import Globals  # import Zope 2 dependencies in order

from BTrees.IIBTree import IIBTree, IISet
from OFS.PropertyManager import PropertyManager
from OFS.SimpleItem import SimpleItem
from Products.PluginIndexes.common.util import parseIndexRequest
from Products.ZCatalog.CatalogBrains import AbstractCatalogBrain
from transaction.interfaces import IDataManager
from zope.app.component.hooks import getSite
from zope.component import queryAdapter
from zope.interface import implements

try:
    from Products.CMFCore.utils import getToolByName
except ImportError:
    from alm.solrindex.utils import getToolByName

from alm.solrindex.interfaces import ISolrConnectionManager
from alm.solrindex.interfaces import ISolrIndex
from alm.solrindex.interfaces import ISolrIndexingWrapper
from alm.solrindex.schema import SolrSchema
from alm.solrindex.solrpycore import SolrConnection

disable_solr = os.environ.get('DISABLE_SOLR')

log = logging.getLogger(__name__)


class SolrIndex(PropertyManager, SimpleItem):

    implements(ISolrIndex)

    _properties = (
        {'id': 'solr_uri_static', 'type': 'string', 'mode': 'w',
            'description':
            'The Solr URI, for example, "http://localhost:8983/solr". '
            'You should leave this empty if you set solr_uri_env_var.'},
        {'id': 'solr_uri_env_var', 'type': 'string', 'mode': 'w',
            'description':
            'The name of an environment variable that will provide '
            'the Solr URI.  Ignored if solr_uri_static is non-empty.'},
        {'id': 'solr_uri', 'type': 'string', 'mode': '',
            'description': 'The effective Solr URI (read-only)'},
        {'id': 'expected_encodings', 'type': 'lines', 'mode': 'w',
            'description':
            'The list of encodings to try to decode from before encoding '
            'to UTF-8 to submit to Solr.'},
        )

    manage_options = PropertyManager.manage_options + SimpleItem.manage_options

    _v_temp_cm = None  # An ISolrConnectionManager used during initialization
    _highlighting = {} # A dict mapping a hash of the catalog filters
                       # to highlighting data
    solr_uri_static = ''
    solr_uri_env_var = ''
    expected_encodings = ['utf-8']

    def __init__(self, id, solr_uri_static='', expected_encodings=None):
        self.id = id
        self.solr_uri_static = solr_uri_static
        if expected_encodings is not None:
            self.expected_encodings = expected_encodings

    @property
    def solr_uri(self):
        if self.solr_uri_static:
            return self.solr_uri_static
        elif self.solr_uri_env_var:
            return os.environ[self.solr_uri_env_var]
        elif 'solr_uri' in self.__dict__:
            # b/w compat
            return self.__dict__['solr_uri']
        else:
            raise ValueError("No Solr URI provided")

    @property
    def connection_manager(self):
        if disable_solr:
            raise AssertionError("Solr indexing is temporarily disabled")

        jar = self._p_jar
        oid = self._p_oid

        if jar is None or oid is None:
            # Not yet stored in ZODB, so use _v_temp_cm
            manager = self._v_temp_cm
            if manager is None or manager.solr_uri != self.solr_uri:
                self._v_temp_cm = manager = ISolrConnectionManager(self)

        else:
            fc = getattr(jar, 'foreign_connections', None)
            if fc is None:
                jar.foreign_connections = fc = {}

            manager = fc.get(oid)
            if manager is None or manager.solr_uri != self.solr_uri:
                manager = ISolrConnectionManager(self)
                fc[oid] = manager

        return manager

    def getIndexSourceNames(self):
        """Get a sequence of attribute names that are indexed by the index.
        """
        if disable_solr:
            return []

        cm = self.connection_manager
        names = [field.name for field in cm.schema.fields]
        return names

    def getEntryForObject(self, documentId, default=None):
        """Return the information stored for documentId"""
        if disable_solr:
            return None

        cm = self.connection_manager
        uniqueKey = cm.schema.uniqueKey
        response = cm.connection.query(
            q='%s:"%d"' % (uniqueKey, documentId), fields='*')
        results = list(response)
        if results:
            return results[0]
        else:
            return None

    def index_object(self, documentId, obj, threshold=None):
        """Index an object.

        'documentId' is the integer ID of the document.
        'obj' is the object to be indexed.
        'threshold' is the number of words to process between committing
        subtransactions.  If None, subtransactions are disabled.
        """
        if disable_solr:
            return 0

        cm = self.connection_manager
        values = {}
        uniqueKey = cm.schema.uniqueKey
        values[uniqueKey] = documentId
        obj = queryAdapter(obj, ISolrIndexingWrapper, default=obj)

        for field in cm.schema.fields:
            name = field.name
            if name == uniqueKey:
                continue
            value = getattr(obj, name, None)
            if callable(value):
                value = value()
            value_list = field.handler.convert(value)
            if value_list:
                values[name] = value_list

        cm.set_changed()
        log.debug("indexing %d", documentId)
        cm.connection.add(**values)
        return 1

    def unindex_object(self, documentId):
        """Remove the documentId from the index."""
        if disable_solr:
            return

        cm = self.connection_manager
        cm.set_changed()
        log.debug("unindexing %d", documentId)
        cm.connection.delete(documentId)

    def _apply_index(self, request, cid=''):
        """Apply query specified by request, a mapping containing the query.

        Returns two objects on success: the resultSet containing the
        matching record numbers, and a tuple containing the names of
        the fields used.

        Returns None if request is not valid for this index.
        """
        if disable_solr:
            return None

        cm = self.connection_manager
        q = []           # List of query texts to pass as "q"
        queried = []     # List of field names queried
        highlighted = [] # List of field names highlighted
        solr_params = {}

        # Get the Solr parameters from the catalog query
        if request.has_key('solr_params'):
            solr_params.update(request['solr_params'])

        # Include parameters from field queries
        for field in cm.schema.fields:
            name = field.name
            if field.stored:
                highlighted.append(name)
            if not request.has_key(name):
                continue
            field_query = request[name]
            field_params = field.handler.parse_query(field, field_query)
            if field_params:
                queried.append(name)
                for k in field_params:
                    to_add = field_params[k]
                    if k not in solr_params:
                        solr_params[k] = to_add
                    else:
                        # add to the list
                        v = solr_params[k]
                        if not isinstance(v, list):
                            v = [v]
                            solr_params[k] = v
                        if isinstance(to_add, basestring):
                            v.append(to_add)
                        else:
                            v.extend(to_add)

        if not solr_params:
            return None

        solr_params['fields'] = cm.schema.uniqueKey
        # We add highlighting by default for any field that is marked as stored.
        # To disable this behavior, pass in a value for 'highlight' in
        # solr_params. None will completely disable highlighting, True defaults
        # to the list of fields queried, a specific list of names will narrow
        # the list.
        if 'highlight' not in solr_params and highlighted:
            solr_params['highlight'] = highlighted
        if not solr_params.get('q'):
            # Solr requires a 'q' parameter, so provide an all-inclusive one
            solr_params['q'] = '*:*'

        log.debug("querying: %r", solr_params)

        # http://wiki.apache.org/solr/FAQ#Why_don.27t_International_Characters_Work.3F
        # Decode all strings using list from `expected_encodings`,
        # then transcode to UTF8
        transcoded_params = {}
        for key, val in solr_params.items():
            enc_val = None
            if isinstance(val, basestring):
                enc_val = self._encode_param(val)
            elif isinstance(val, list):
                enc_val = []
                for v in val:
                    if isinstance(v, basestring):
                        enc_val.append(self._encode_param(v))
                    else:
                        enc_val.append(v)
            else:
                enc_val = val
            transcoded_params[key] = enc_val

        response = cm.connection.query(**transcoded_params)
        #response = cm.connection.query(**solr_params)
        if request.has_key('solr_callback'):
            # Call a function with the Solr response object
            callback = request['solr_callback']
            callback(response)

        catalog = get_catalog(self)
        if transcoded_params.get('highlight', None) is None:
            if catalog._v_brains is not AbstractCatalogBrain:
                catalog.useBrains(AbstractCatalogBrain)
        else:
            hkey = sorted([(fname, request.get(fname))
                           for fname in queried])
            self._highlighting[tuple(hkey)] = response.highlighting
            if catalog._v_brains is not HighlightingBrain:
                catalog.useBrains(HighlightingBrain)

        uniqueKey = cm.schema.uniqueKey
        result = IIBTree()
        for r in response:
            result[r[uniqueKey]] = int(r.get('score', 0) * 1000)

        return result, queried

    def _encode_param(self, val):
        decoded_val = None
        for encoding in self.expected_encodings:
            try:
                decoded_val = force_unicode(val, encoding)
            except UnicodeDecodeError:
                continue
        if decoded_val is None:
            # Our escape hatch; if none of the expected encodings
            # work, we fall back to UTF8 and replace characters
            decoded_val = force_unicode(val, encoding='utf-8',
                                             errors='replace')
        # We don't want to raise a UnicodeEncodeError here
        return decoded_val.encode('utf-8', 'replace')

    ## The ZCatalog Index management screen uses these methods ##

    def numObjects(self):
        """Return number of unique words in the index"""
        return 0

    def indexSize(self):
        """Return the number of indexed objects"""
        if disable_solr:
            return 0

        cm = self.connection_manager
        response = cm.connection.query(q='*:*', rows='0')
        return int(response.numFound)

    def clear(self):
        """Empty the index"""
        if disable_solr:
            return

        cm = self.connection_manager
        cm.set_changed()
        cm.connection.delete_query('*:*')


class NoRollbackSavepoint:

    def __init__(self, datamanager):
        self.datamanager = datamanager

    def rollback(self):
        pass


class SolrConnectionManager(object):
    implements(ISolrConnectionManager, IDataManager)

    def __init__(self, solr_index, connection_factory=SolrConnection):
        self.solr_uri = solr_index.solr_uri
        self._joined = False
        self._connection_factory = connection_factory
        self._connection = connection_factory(self.solr_uri)
        self.schema = SolrSchema(self.solr_uri)

    @property
    def connection(self):
        c = self._connection
        if c is None:
            c = self._connection_factory(self.solr_uri)
            self._connection = c
        return c

    def set_changed(self):
        if not self._joined:
            transaction.get().join(self)
            self._joined = True

    def abort(self, transaction):
        try:
            c = self._connection
            if c is not None:
                self._connection = None
                c.close()
        finally:
            self._joined = False

    def tpc_begin(self, transaction):
        pass

    def commit(self, transaction):
        pass

    def tpc_vote(self, transaction):
        # ensure connection is open
        dummy = self.connection

    def tpc_finish(self, transaction):
        try:
            try:
                self.connection.commit()
            except:
                self.abort(transaction)
                raise
        finally:
            self._joined = False

    def tpc_abort(self, transaction):
        pass

    def sortKey(self):
        return self.solr_uri

    def savepoint(self, optimistic=False):
        return NoRollbackSavepoint(self)

def force_unicode(s, encoding='utf-8', errors='strict'):
    if isinstance(s, unicode):
        return s
    try:
        if not isinstance(s, basestring,):
            if hasattr(s, '__unicode__'):
                s = unicode(s)
            else:
                try:
                    s = unicode(str(s), encoding, errors)
                except UnicodeEncodeError:
                    if not isinstance(s, Exception):
                        raise
                    # If we get to here, the caller has passed in an Exception
                    # subclass populated with non-ASCII data without special
                    # handling to display as a string. We need to handle this
                    # without raising a further exception. We do an
                    # approximation to what the Exception's standard str()
                    # output should be.
                    s = ' '.join([force_unicode(arg, encoding, errors)
                                  for arg in s])
        elif not isinstance(s, unicode):
            # Note: We use .decode() here, instead of unicode(s, encoding,
            # errors), so that if s is a SafeString, it ends up being a
            # SafeUnicode at the end.
            s = s.decode(encoding, errors)
    except UnicodeDecodeError, e:
       # If we get to here, the caller has passed in an Exception
       # subclass populated with non-ASCII bytestring data without a
       # working unicode method. Try to handle this without raising a
       # further exception by individually forcing the exception args
       # to unicode.
       s = ' '.join([force_unicode(arg, encoding, errors) for arg in s])

    return s


class HighlightingBrain(AbstractCatalogBrain):

    def getHighlighting(self, combine_fields=True, **kwargs):
        """This method retrieves the stored highlighting data for a given
            set of fields.
        `combine_fields` forces the output to a single list of highlighted
            snippets.
        If `combine_fields` is False, the output is a dictionary with the
            field name as key and a list of the highlighted snippets as the
            value.
        The `kwargs` parameter is required to be able match up
            a given set of highlights with the original query issued, when
            multiple queries happen in a single request. If none are passed in,
            the method will return an empty dictionary (or empty list, as above).
        """
        catalog = get_catalog(self)
        indexes = get_solr_indexes(catalog)
        result = {}
        rid = unicode(self.getRID())
        for index in indexes:
            hkey = sorted(kwargs.items())
            highlights = index._highlighting.get(tuple(hkey), None)
            if highlights is None:
                continue
            brain_highlights = highlights.get(rid, {})

            for key in kwargs:
                val = brain_highlights.get(key, None)
                if val is None:
                    continue
                if key not in result:
                    result[key] = []
                if isinstance(val, (tuple,list)):
                    result[key].extend(val)
                else:
                    result[key].append(val)

        if combine_fields:
            combined = []
            for val in result.values():
                combined.extend(val)
            return combined
        else:
            return result

def get_catalog(obj):
    catalog = getToolByName(obj, 'portal_catalog')
    if hasattr(catalog, '_catalog'):
        catalog = catalog._catalog
    return catalog

def get_solr_indexes(catalog):
    # Use getIndex to ensure the object is wrapped correctly
    return [catalog.getIndex(name)
            for name, idx in catalog.indexes.items()
                if ISolrIndex.providedBy(idx)]

