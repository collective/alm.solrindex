
import unittest
from zope.testing.cleanup import cleanUp

class SolrIndexTests(unittest.TestCase):

    def setUp(self):
        cleanUp()

    def tearDown(self):
        cleanUp()

    def _getTargetClass(self):
        from alm.solrindex.index import SolrIndex
        return SolrIndex

    def _makeOne(self, id, solr_uri):
        obj = self._getTargetClass()(id, solr_uri)
        obj._p_oid = '8byteoid'
        obj._p_jar = DummyZODBConnection()
        return obj

    def _registerConnectionManager(self):
        from alm.solrindex.interfaces import ISolrConnectionManager
        from alm.solrindex.interfaces import ISolrIndex
        from zope.component import getGlobalSiteManager
        getGlobalSiteManager().registerAdapter(
            DummyConnectionManager, (ISolrIndex,), ISolrConnectionManager)

    def test_verifyImplements(self):
        from zope.interface.verify import verifyClass
        from alm.solrindex.interfaces import ISolrIndex
        verifyClass(ISolrIndex, self._getTargetClass())

    def test_verifyProvides(self):
        from zope.interface.verify import verifyObject
        from alm.solrindex.interfaces import ISolrIndex
        self._registerConnectionManager()
        obj = self._makeOne('id', 'someuri')
        verifyObject(ISolrIndex, obj)

    def test_connection_manager(self):
        self._registerConnectionManager()
        index = self._makeOne('id', 'someuri')
        cm = index.connection_manager
        cm2  = index.connection_manager
        self.assert_(cm is cm2)
        self.assert_(cm.index is index)

    def test_getIndexSourceNames(self):
        self._registerConnectionManager()
        index = self._makeOne('id', 'someuri')
        self.assertEqual(index.getIndexSourceNames(), ['f1', 'f2'])

    def test_getEntryForObject(self):
        self._registerConnectionManager()
        index = self._makeOne('id', 'someuri')
        cm = index.connection_manager
        cm.connection.results = [[{'docid': 2}]]
        entry = index.getEntryForObject(2)
        self.assertEqual(entry, {'docid': 2})
        self.assertEqual(cm.connection.queries,
            [{'q': 'docid:2', 'fields': '*', 'rows': '0'}])

    def test_index_object(self):
        self._registerConnectionManager()
        index = self._makeOne('id', 'someuri')
        cm = index.connection_manager
        self.assertFalse(cm.changed)
        index.index_object(2, DummyIndexableObject())
        self.assertTrue(cm.changed)
        self.assertEqual(cm.connection.added,
            [{'f1': ['a'], 'f2': ['b'], 'docid': 2}])

    def test_unindex_object(self):
        self._registerConnectionManager()
        index = self._makeOne('id', 'someuri')
        cm = index.connection_manager
        self.assertFalse(cm.changed)
        index.unindex_object(2)
        self.assertTrue(cm.changed)
        self.assertEqual(cm.connection.deleted, [2])

    def test__apply_index_basic(self):
        self._registerConnectionManager()
        index = self._makeOne('id', 'someuri')
        cm = index.connection_manager
        request = {'f1': 'somequery'}
        cm.connection.results = [[{'docid': 5}]]
        result, queried = index._apply_index(request)
        self.assertEqual(queried, ['f1'])
        self.assertEqual(dict(result.items()), {5: 0})
        self.assertFalse(cm.changed)
        self.assertEqual(cm.connection.queries, [
            {'q': "f1:somequery", 'fields': 'docid'}])

    def test__apply_index_with_scores(self):
        self._registerConnectionManager()
        index = self._makeOne('id', 'someuri')
        cm = index.connection_manager
        request = {'f1': 'somequery'}
        cm.connection.results = [[{'docid': 5, 'score': 0.25}]]
        result, queried = index._apply_index(request)
        self.assertEqual(queried, ['f1'])
        self.assertEqual(dict(result.items()), {5: 250})
        self.assertFalse(cm.changed)
        self.assertEqual(cm.connection.queries, [
            {'q': "f1:somequery", 'fields': 'docid'}])

    def test__apply_index_no_matching_fields(self):
        self._registerConnectionManager()
        index = self._makeOne('id', 'someuri')
        cm = index.connection_manager
        request = {'f99': 'somequery'}
        res = index._apply_index(request)
        self.assertEqual(res, None)

    def test__apply_index_extra_solr_params(self):
        self._registerConnectionManager()
        index = self._makeOne('id', 'someuri')
        cm = index.connection_manager
        request = {
            'f1': 'somequery',
            'solr_params': {'q': 'stuff', 'spellcheck': 'true'},
            }
        cm.connection.results = [[{'docid': 5}]]
        result, queried = index._apply_index(request)
        self.assertEqual(queried, ['f1'])
        self.assertEqual(dict(result.items()), {5: 0})
        self.assertFalse(cm.changed)
        self.assertEqual(cm.connection.queries, [{
                'q': ['stuff', 'f1:somequery'],
                'fields': 'docid',
                'spellcheck': 'true',
                }])

    def test__apply_index_with_callback(self):
        self._registerConnectionManager()
        index = self._makeOne('solr', 'someuri')
        cm = index.connection_manager
        responses = []
        request = {
            'f1': 'somequery',
            'solr_callback': responses.append,
            }
        cm.connection.results = [[{'docid': 5}]]
        result, queried = index._apply_index(request)
        self.assertEqual(queried, ['f1'])
        self.assertEqual(dict(result.items()), {5: 0})
        self.assertFalse(cm.changed)
        self.assertEqual(cm.connection.queries, [
            {'q': 'f1:somequery', 'fields': 'docid'}])
        self.assertEqual(responses, [[{'docid': 5}]])

    def test_indexSize(self):
        self._registerConnectionManager()
        index = self._makeOne('id', 'someuri')
        cm = index.connection_manager
        cm.connection.results = [DummySolrResult(4)]
        count = index.indexSize()
        self.assertEqual(count, 4)
        self.assertFalse(cm.changed)

    def test_clear(self):
        self._registerConnectionManager()
        index = self._makeOne('id', 'someuri')
        cm = index.connection_manager
        self.assertFalse(cm.changed)
        index.clear()
        self.assertTrue(cm.changed)
        self.assertEqual(cm.connection.delete_queries, ['docid:[* TO *]'])

    def test_change_solr_uri(self):
        self._registerConnectionManager()
        index = self._makeOne('id', 'someuri')
        cm1 = index.connection_manager
        index.solr_uri = 'otheruri'
        cm2 = index.connection_manager
        self.assertFalse(cm1 is cm2)


class DummyZODBConnection:
    def register(self, obj):
        pass

class DummyConnectionManager:
    def __init__(self, index):
        self.index = index
        self.schema = DummySchema()
        self.connection = DummySolrConnection()
        self.changed = False
        self.solr_uri = 'someuri'

    def set_changed(self):
        self.changed = True

class DummySolrConnection:
    def __init__(self):
        self.queries = []
        self.results = []
        self.added = []
        self.deleted = []
        self.delete_queries = []

    def query(self, **args):
        self.queries.append(args)
        return self.results.pop(0)

    def add(self, **args):
        self.added.append(args)

    def delete(self, id):
        self.deleted.append(id)

    def delete_query(self, q):
        self.delete_queries.append(q)

class DummySchema:
    uniqueKey = 'docid'
    def __init__(self):
        self.fields = []
        for name in ('f1', 'f2'):
            self.fields.append(DummyField(name))

class DummyField:
    def __init__(self, name):
        self.name = name
        self.handler = DummyFieldHandler()

class DummyFieldHandler:
    def parse_query(self, field, field_query):
        return {'q': '%s:%s' % (field.name, field_query)}
    def convert(self, value):
        return [value]

class DummySolrResult:
    def __init__(self, numFound):
        self.numFound = numFound

class DummyIndexableObject:
    f1 = 'a'

    def f2(self):
        return 'b'

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SolrIndexTests))
    return suite
