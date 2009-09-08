
import Globals  # import Zope 2 dependencies in order

from alm.solrindex.interfaces import ISolrConnectionManager
from alm.solrindex.interfaces import ISolrIndexData
from alm.solrindex.interfaces import ISolrIndex
from alm.solrindex.interfaces import ISolrIndexingWrapper
from alm.solrindex.schema import SolrSchema
from BTrees.IIBTree import IIBTree, IISet
from OFS.SimpleItem import SimpleItem
from Products.PluginIndexes.common.util import parseIndexRequest
from solr import SolrConnection
from transaction.interfaces import IDataManager
from zope.component import queryAdapter
from zope.interface import implements
import transaction


class SolrIndex(SimpleItem):

    implements(ISolrIndex)

    def __init__(self, id, solr_uri):
        self.id = id
        self.solr_uri = solr_uri
        self.enable_indexing = True
        self.enable_querying = True

        # Test the connection
        ISolrConnectionManager(self)

    @property
    def connection_manager(self):
        jar = self._p_jar
        oid = self._p_oid
        if jar is None or oid is None:
            raise AssertionError("SolrIndex object not yet stored in ZODB")

        fc = getattr(jar, 'foreign_connections', None)
        if fc is None:
            jar.foreign_connections = fc = {}

        manager = fc.get(oid)
        if manager is None:
            manager = ISolrConnectionManager(self)
            fc[oid] = manager

        return manager

    def getIndexSourceNames(self):
        """Get a sequence of attribute names that are indexed by the index.
        """
        cm = self.connection_manager
        names = [field.name for field in cm.schema.fields]
        return names

    def getEntryForObject(self, documentId, default=None):
        """Return the information stored for documentId"""
        cm = self.connection_manager
        uniqueKey = cm.schema.uniqueKey
        response = cm.connection.query(
            q='%s:%d' % (uniqueKey, documentId), fields='*', rows='0')
        if response:
            return response[0]
        else:
            return None

    def index_object(self, documentId, obj, threshold=None):
        """Index an object.

        'documentId' is the integer ID of the document.
        'obj' is the object to be indexed.
        'threshold' is the number of words to process between committing
        subtransactions.  If None, subtransactions are disabled.
        """
        if not self.enable_indexing:
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
            if value is not None:
                value = queryAdapter(value, ISolrIndexData, default=value)
                if value is not None:
                    values[name] = value

        cm.set_changed()
        cm.connection.add(**values)
        return 1

    def unindex_object(self, documentId):
        """Remove the documentId from the index."""
        if not self.enable_indexing:
            return

        cm = self.connection_manager
        cm.set_changed()
        cm.connection.delete(documentId)

    def _apply_index(self, request, cid=''):
        """Apply query specified by request, a mapping containing the query.

        Returns two objects on success: the resultSet containing the
        matching record numbers, and a tuple containing the names of
        the fields used.

        Returns None if request is not valid for this index.
        """
        if not self.enable_querying:
            return None

        cm = self.connection_manager
        q = []           # List of query texts to pass as "q"
        queried = []     # List of field names queried
        callback = None  # Function to call with the Solr response object

        # extract Solr-specific parameters from the catalog query
        solr_params = {'fields': cm.schema.uniqueKey}
        if self.id in request:
            solr_params.update(request[self.id])
            if 'q' in solr_params:
                q_part = solr_params.pop('q')
                q.append(q_part)
            if 'callback' in solr_params:
                # Call a function with the Solr response object
                callback = solr_params.pop('callback')
        else:
            solr_params = {}

        # generate a query string from field queries
        for field in cm.schema.fields:
            name = field.name
            if name not in request:
                continue
            field_query = request[name]
            q_part = field.query_converter(field, field_query)
            if q_part is not None:
                q.append(q_part)
                queried.append(name)

        if not q:
            return None

        solr_params['q'] = ' AND '.join(q)
        response = cm.connection.query(**solr_params)
        if callback is not None:
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
        cm = self.connection_manager
        uniqueKey = cm.schema.uniqueKey
        response = cm.connection.query(q='%s:[* TO *]' % uniqueKey, rows='0')
        return response.numFound

    def clear(self):
        """Empty the index"""
        cm = self.connection_manager
        cm.set_changed()
        uniqueKey = cm.schema.uniqueKey
        cm.connection.delete_query('%s:[* TO *]' % uniqueKey)


class SolrConnectionManager(object):
    implements(ISolrConnectionManager, IDataManager)

    def __init__(self, solr_index):
        self.solr_uri = solr_index.solr_uri
        self._joined = False
        self.connection = SolrConnection(self.solr_uri)
        self.schema = SolrSchema(self.solr_uri)

    def set_changed(self):
        if not self._joined:
            transaction.get().join(self)
            self._joined = True

    def abort(self, transaction):
        pass

    def tpc_begin(self, transaction):
        pass

    def commit(self, transaction):
        pass

    def tpc_vote(self, transaction):
        pass

    def tpc_finish(self, transaction):
        try:
            try:
                self.connection.commit()
            except:
                self.connection.close()
                # we might want to clean up here
                raise
        finally:
            self._joined = False

    def tpc_abort(self, transaction):
        try:
            self.connection.close()
        finally:
            self._joined = False

    def sortKey(self):
        return self.solr_uri

