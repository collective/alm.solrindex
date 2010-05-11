"""SolrIndex and SolrConnectionManager"""

import Globals  # import Zope 2 dependencies in order

from alm.solrindex.interfaces import ISolrConnectionManager
from alm.solrindex.interfaces import ISolrIndex
from alm.solrindex.interfaces import ISolrIndexingWrapper
from alm.solrindex.schema import SolrSchema
from alm.solrindex.solrpycore import SolrConnection
from BTrees.IIBTree import IIBTree, IISet
from OFS.PropertyManager import PropertyManager
from OFS.SimpleItem import SimpleItem
from Products.PluginIndexes.common.util import parseIndexRequest
from transaction.interfaces import IDataManager
from zope.component import queryAdapter
from zope.interface import implements
import logging
import os
import transaction

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
        )

    manage_options = PropertyManager.manage_options + SimpleItem.manage_options

    _v_temp_cm = None  # An ISolrConnectionManager used during initialization
    solr_uri_static = ''
    solr_uri_env_var = ''

    def __init__(self, id, solr_uri_static=''):
        self.id = id
        self.solr_uri_static = solr_uri_static

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
        solr_params = {}

        # Get the Solr parameters from the catalog query
        if request.has_key('solr_params'):
            solr_params.update(request['solr_params'])

        # Include parameters from field queries
        for field in cm.schema.fields:
            name = field.name
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
        if not solr_params.get('q'):
            # Solr requires a 'q' parameter, so provide an all-inclusive one
            solr_params['q'] = '*:*'

        log.debug("querying: %r", solr_params)

        response = cm.connection.query(**solr_params)
        if request.has_key('solr_callback'):
            # Call a function with the Solr response object
            callback = request['solr_callback']
            callback(response)

        uniqueKey = cm.schema.uniqueKey
        result = IIBTree()
        for r in response:
            result[r[uniqueKey]] = int(r.get('score', 0) * 1000)

        return result, queried

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
