
import unittest

class SolrEscapeTests(unittest.TestCase):

    def _callFUT(self, s):
        from alm.solrindex.components import solr_escape
        return solr_escape(s)

    def test_empty(self):
        self.assertEqual(self._callFUT(''), '')

    def test_simple(self):
        self.assertEqual(self._callFUT('abc'), 'abc')

    def test_unicode(self):
        self.assertEqual(self._callFUT(u'smile \u30b7'), u'smile \u30b7')

    def test_quotes(self):
        self.assertEqual(self._callFUT(u'I am "misquoted"'),
            u'I am \\"misquoted\\"')

    def test_all_escaped_characters(self):
        s = '\\:?*~"^][}{)(!|&+-'
        expect = ''.join('\\' + c for c in s)
        actual = self._callFUT(s)
        self.assertEqual(actual, expect)


class DefaultQueryConverterTests(unittest.TestCase):

    def _getTargetClass(self):
        from alm.solrindex.components import DefaultQueryConverter
        return DefaultQueryConverter

    def _makeOne(self):
        return self._getTargetClass()()

    def test_verifyImplements(self):
        from zope.interface.verify import verifyClass
        from alm.solrindex.interfaces import ISolrQueryConverter
        verifyClass(ISolrQueryConverter, self._getTargetClass())

    def test_verifyProvides(self):
        from zope.interface.verify import verifyObject
        from alm.solrindex.interfaces import ISolrQueryConverter
        verifyObject(ISolrQueryConverter, self._makeOne())

    def test_simple(self):
        field = DummyField()
        field_query = 'hello'
        interp = self._makeOne()
        q_item = interp(field, field_query)
        self.assert_(isinstance(q_item, unicode))
        self.assertEqual(q_item, u'dummyfield:"hello"')

    def test_escaped(self):
        field = DummyField()
        field_query = u'Hello "Solr"! \u30b7'
        interp = self._makeOne()
        q_item = interp(field, field_query)
        self.assert_(isinstance(q_item, unicode))
        self.assertEqual(q_item, u'dummyfield:"Hello \\"Solr\\"\\! \u30b7"')


class DummyField:
    name = 'dummyfield'
