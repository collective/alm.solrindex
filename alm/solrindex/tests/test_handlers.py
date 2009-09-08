
import unittest

class SolrEscapeTests(unittest.TestCase):

    def _callFUT(self, s):
        from alm.solrindex.handlers import solr_escape
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


class DefaultFieldHandlerTests(unittest.TestCase):

    def _getTargetClass(self):
        from alm.solrindex.handlers import DefaultFieldHandler
        return DefaultFieldHandler

    def _makeOne(self):
        return self._getTargetClass()()

    def test_verifyImplements(self):
        from zope.interface.verify import verifyClass
        from alm.solrindex.interfaces import ISolrFieldHandler
        verifyClass(ISolrFieldHandler, self._getTargetClass())

    def test_verifyProvides(self):
        from zope.interface.verify import verifyObject
        from alm.solrindex.interfaces import ISolrFieldHandler
        verifyObject(ISolrFieldHandler, self._makeOne())

    def test_simple_query(self):
        field = DummyField()
        field_query = 'hello'
        handler = self._makeOne()
        q_item = handler.parse_query(field, field_query)
        self.assert_(isinstance(q_item, unicode))
        self.assertEqual(q_item, u'dummyfield:"hello"')

    def test_escaped_query(self):
        field = DummyField()
        field_query = u'Hello "Solr"! \u30b7'
        handler = self._makeOne()
        q_item = handler.parse_query(field, field_query)
        self.assert_(isinstance(q_item, unicode))
        self.assertEqual(q_item, u'dummyfield:"Hello \\"Solr\\"\\! \u30b7"')

    def test_query_multiple_default_operator(self):
        field = DummyField()
        field_query = ['news', 'sports', '"local"']
        handler = self._makeOne()
        q_item = handler.parse_query(field, field_query)
        self.assert_(isinstance(q_item, unicode))
        self.assertEqual(q_item,
            u'dummyfield:("news" OR "sports" OR "\\"local\\"")')

    def test_query_multiple_and_operator(self):
        field = DummyField()
        field_query = {
            'query': ['news', 'sports', '"local"'],
            'operator': 'and',
            }
        handler = self._makeOne()
        q_item = handler.parse_query(field, field_query)
        self.assert_(isinstance(q_item, unicode))
        self.assertEqual(q_item,
            u'dummyfield:("news" AND "sports" AND "\\"local\\"")')

    def test_convert_none(self):
        handler = self._makeOne()
        self.assertEqual(handler.convert(None), ())

    def test_convert_string(self):
        handler = self._makeOne()
        actual = handler.convert('abc')
        self.assertEqual(len(actual), 1)
        self.assert_(isinstance(actual[0], unicode))
        self.assertEqual(actual, [u'abc'])

    def test_convert_multiple(self):
        handler = self._makeOne()
        actual = handler.convert(('abc', 'def'))
        self.assertEqual(len(actual), 2)
        self.assert_(isinstance(actual[0], unicode))
        self.assertEqual(actual, [u'abc', u'def'])


class DateFieldHandlerTests(unittest.TestCase):

    def _getTargetClass(self):
        from alm.solrindex.handlers import DateFieldHandler
        return DateFieldHandler

    def _makeOne(self):
        return self._getTargetClass()()

    def test_verifyImplements(self):
        from zope.interface.verify import verifyClass
        from alm.solrindex.interfaces import ISolrFieldHandler
        verifyClass(ISolrFieldHandler, self._getTargetClass())

    def test_verifyProvides(self):
        from zope.interface.verify import verifyObject
        from alm.solrindex.interfaces import ISolrFieldHandler
        verifyObject(ISolrFieldHandler, self._makeOne())

    def test_convert_none(self):
        handler = self._makeOne()
        self.assertEqual(handler.convert(None), ())

    def test_convert_datetime(self):
        import datetime
        handler = self._makeOne()
        actual = handler.convert(datetime.datetime(2009, 9, 8, 11, 51, 30))
        self.assertEqual(actual, ['2009-09-08T11:51:30.000Z'])

    def test_convert_date(self):
        import datetime
        handler = self._makeOne()
        actual = handler.convert(datetime.date(2009, 9, 8))
        self.assertEqual(actual, ['2009-09-08T00:00:00.000Z'])

    def test_convert_multiple_dates(self):
        import datetime
        handler = self._makeOne()
        actual = handler.convert(
            [datetime.date(2009, 9, 8), datetime.date(2009, 9, 9)])
        self.assertEqual(actual,
            ['2009-09-08T00:00:00.000Z', '2009-09-09T00:00:00.000Z'])

    def test_convert_string(self):
        handler = self._makeOne()
        actual = handler.convert('September 8, 2009 11:51:31.512 AM UTC')
        self.assertEqual(actual, ['2009-09-08T11:51:31.512Z'])

    def test_convert_float(self):
        import calendar
        t = calendar.timegm((2009, 9, 8, 11, 51, 32))
        handler = self._makeOne()
        actual = handler.convert(t)
        self.assertEqual(actual, ['2009-09-08T11:51:32.000Z'])

    def test_convert_DateTime(self):
        from DateTime.DateTime import DateTime
        t = DateTime('2009-09-08 11:51:34.000 UTC')
        handler = self._makeOne()
        actual = handler.convert(t)
        self.assertEqual(actual, ['2009-09-08T11:51:34.000Z'])

    def test_convert_other(self):
        handler = self._makeOne()
        self.assertRaises(TypeError, handler.convert, object())


class DummyField:
    name = 'dummyfield'
