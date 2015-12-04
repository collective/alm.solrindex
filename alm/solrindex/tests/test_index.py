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

    def _makeOne(self, id, solr_uri_static=''):
        obj = self._getTargetClass()(id, solr_uri_static)
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
        cm2 = index.connection_manager
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
            [{'q': 'docid:"2"', 'fields': '*'}])

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
            'q': 'stuff f1:somequery',
            'fields': 'docid',
            'spellcheck': 'true',
            }])

    def test__apply_index_dismax_no_q(self):
        self._registerConnectionManager()
        index = self._makeOne('id', 'someuri')
        cm = index.connection_manager
        request = {
            'solr_params': {'defType': 'dismax'},
            }
        cm.connection.results = [[{'docid': 5}]]
        result, queried = index._apply_index(request)
        self.assertFalse(cm.changed)
        self.assertEqual(cm.connection.queries, [{
                'q': '',
                'fields': 'docid',
                'defType': 'dismax',
                'q.alt': '*:*',
                }])

    def test__apply_index_dismax(self):
        self._registerConnectionManager()
        index = self._makeOne('id', 'someuri')
        cm = index.connection_manager
        request = {
            'f1': 'somequery',
            'solr_params': {'q': 'stuff', 'defType': 'dismax'},
            }
        cm.connection.results = [[{'docid': 5}]]
        result, queried = index._apply_index(request)
        self.assertEqual(queried, ['f1'])
        self.assertEqual(dict(result.items()), {5: 0})
        self.assertFalse(cm.changed)
        self.assertEqual(cm.connection.queries, [{
            'q': 'stuff f1:somequery',
            'fields': 'docid',
            'defType': 'dismax',
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

    def test__apply_index_with_unicode(self):
        self._registerConnectionManager()
        index = self._makeOne('id', 'someuri')
        cm = index.connection_manager
        request = {'f1': u'\xfcber'}
        cm.connection.results = [[{'docid': 5}]]
        result, queried = index._apply_index(request)
        self.assertEqual(queried, ['f1'])
        self.assertEqual(dict(result.items()), {5: 0})
        self.assertFalse(cm.changed)
        self.assertEqual(cm.connection.queries, [
            {'q': 'f1:\xc3\xbcber', 'fields': 'docid'}])

    def test__apply_index_with_highlighting(self):
        self._registerConnectionManager()
        index = self._makeOne('id', 'someuri')
        cm = index.connection_manager
        f2 = cm.schema.fields[1]
        request = {'f1': 'someuri',
                   'solr_params': {'highlight': [f2.name]}}
        cm.connection.results = [[{'docid': 5}]]
        f2.stored = True
        result, queried = index._apply_index(request)
        self.assertEqual(queried, ['f1'])
        self.assertEqual(dict(result.items()), {5: 0})
        self.assertFalse(cm.changed)
        self.assertEqual(cm.connection.queries, [
            {'q': 'f1:someuri', 'fields': 'docid', 'highlight': [f2.name]}])

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
        self.assertEqual(cm.connection.delete_queries, ['*:*'])

    def test_change_solr_uri(self):
        self._registerConnectionManager()
        index = self._makeOne('id', 'someuri')
        cm1 = index.connection_manager
        index.solr_uri_static = 'otheruri'
        cm2 = index.connection_manager
        self.assertFalse(cm1 is cm2)

    def test_get_solr_connection_from_zodb(self):
        self._registerConnectionManager()
        index = self._makeOne('id', 'someuri')
        index._p_oid = '8byteoid'
        index._p_jar = zodbc = DummyZODBConnection()
        cm = index.connection_manager
        self.assertEqual(len(zodbc.foreign_connections), 1)
        self.assert_(zodbc.foreign_connections['8byteoid'] is cm)

    def test_get_static_solr_uri(self):
        index = self._makeOne('id', 'someuri')
        self.assertEqual(index.solr_uri, 'someuri')

    def test_get_solr_uri_from_environment(self):
        import os
        index = self._makeOne('id')
        index.solr_uri_env_var = 'TEST_SOLR_URI'
        os.environ['TEST_SOLR_URI'] = 'some-uri-from-env'
        try:
            self.assertEqual(index.solr_uri, 'some-uri-from-env')
        finally:
            del os.environ['TEST_SOLR_URI']

    def test_get_bw_compat_solr_uri(self):
        index = self._makeOne('id', '')
        index.__dict__['solr_uri'] = 'bw-compat-uri'
        self.assertEqual(index.solr_uri, 'bw-compat-uri')

    def test_no_solr_uri_specified(self):
        index = self._makeOne('id', '')
        self.assertRaises(ValueError, getattr, index, 'solr_uri')


class SolrConnectionManagerTests(unittest.TestCase):

    def setUp(self):
        cleanUp()

    def tearDown(self):
        cleanUp()

    def _getTargetClass(self):
        from alm.solrindex.index import SolrConnectionManager
        return SolrConnectionManager

    def _makeOne(self, uri=''):
        class DummySolrIndex:
            solr_uri = uri
        obj = self._getTargetClass()(DummySolrIndex(), DummySolrConnection)
        return obj

    def test_verifyImplements(self):
        from zope.interface.verify import verifyClass
        from alm.solrindex.interfaces import ISolrConnectionManager
        verifyClass(ISolrConnectionManager, self._getTargetClass())

    def test_verifyProvides(self):
        from zope.interface.verify import verifyObject
        from alm.solrindex.interfaces import ISolrConnectionManager
        obj = self._makeOne()
        verifyObject(ISolrConnectionManager, obj)

    def test_get_connection(self):
        obj = self._makeOne()
        c = obj.connection
        self.assert_(c is not None)
        self.assert_(obj.connection is c)

    def test_set_changed(self):
        obj = self._makeOne()
        self.assertFalse(obj._joined)
        obj.set_changed()
        self.assertTrue(obj._joined)

    def test_abort(self):
        obj = self._makeOne()
        obj.abort(None)
        self.assertFalse(obj._joined)
        self.assertEqual(obj._connection, None)

    def test_commit(self):
        obj = self._makeOne()
        obj.set_changed()
        obj.tpc_vote(None)
        obj.tpc_finish(None)
        self.assertFalse(obj._joined)
        self.assertEqual(obj._connection.commits, 1)

    def test_commit_after_abort(self):
        obj = self._makeOne()
        obj.abort(None)
        obj.set_changed()
        obj.tpc_vote(None)
        obj.tpc_finish(None)
        self.assertFalse(obj._joined)
        self.assertEqual(obj._connection.commits, 1)


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
    def __init__(self, uri=None):
        self.uri = uri
        self.queries = []
        self.results = []
        self.added = []
        self.deleted = []
        self.delete_queries = []
        self.commits = 0

    def query(self, **args):
        self.queries.append(args)
        return self.results.pop(0)

    def add(self, **args):
        self.added.append(args)

    def delete(self, id):
        self.deleted.append(id)

    def delete_query(self, q):
        self.delete_queries.append(q)

    def close(self):
        pass

    def commit(self):
        self.commits += 1


class DummySchema:
    uniqueKey = 'docid'

    def __init__(self):
        self.fields = []
        for name in ('f1', 'f2'):
            self.fields.append(DummyField(name))


class DummyField:
    def __init__(self, name):
        self.name = name
        self.stored = False
        self.handler = DummyFieldHandler()
        self.type = 'dummy'


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
