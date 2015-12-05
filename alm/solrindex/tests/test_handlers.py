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
        self.assertEqual(self._callFUT(u'I am "quoted"'),
            u'I am \\"quoted\\"')

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
        param = handler.parse_query(field, field_query)
        self.assertEqual(param, {'fq': u'dummyfield:"hello"'})

    def test_escaped_query(self):
        field = DummyField()
        field_query = u'Hello "Solr"! \u30b7'
        handler = self._makeOne()
        param = handler.parse_query(field, field_query)
        self.assertEqual(param,
            {'fq': u'dummyfield:"Hello \\"Solr\\"\\! \u30b7"'})

    def test_query_multiple_default_operator(self):
        field = DummyField()
        field_query = ['news', 'sports', '"local"']
        handler = self._makeOne()
        param = handler.parse_query(field, field_query)
        self.assertEqual(param,
            {'fq': u'dummyfield:("news" OR "sports" OR "\\"local\\"")'})

    def test_query_multiple_and_operator(self):
        field = DummyField()
        field_query = {
            'query': ['news', 'sports', '"local"'],
            'operator': 'and',
            }
        handler = self._makeOne()
        param = handler.parse_query(field, field_query)
        self.assertEqual(param,
            {'fq': u'dummyfield:("news" AND "sports" AND "\\"local\\"")'})

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

    def test_convert_invalid_xml(self):
        handler = self._makeOne()
        actual = handler.convert('A backspace\x08 escaped\x1b!')
        self.assertEqual(len(actual), 1)
        self.assert_(isinstance(actual[0], unicode))
        self.assertEqual(actual, [u'A backspace escaped!'])


class BoolFieldHandlerTests(unittest.TestCase):

    def _getTargetClass(self):
        from alm.solrindex.handlers import BoolFieldHandler
        return BoolFieldHandler

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

    def test_convert_true(self):
        handler = self._makeOne()
        actual = handler.convert(True)
        self.assertEqual(actual, ['true'])

    def test_convert_false(self):
        handler = self._makeOne()
        actual = handler.convert(False)
        self.assertEqual(actual, ['false'])

    def test_convert_list(self):
        handler = self._makeOne()
        actual = handler.convert([False, True, True])
        self.assertEqual(actual, ['false', 'true', 'true'])


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

    def test_parse_query_simple(self):
        from datetime import date
        field = DummyField()
        handler = self._makeOne()
        field_query = date(2015, 12, 4)
        query = handler.parse_query(field, field_query)
        self.assertEqual(query, {'fq': r'dummyfield:"2015\-12\-04T00\:00\:00.000Z"'})

    def test_parse_query_range(self):
        from datetime import date
        field = DummyField()
        handler = self._makeOne()

        query = handler.parse_query(field, {'query': date(2015, 12, 4), 'range': 'min'})
        self.assertEqual(query, {'fq': r'dummyfield:[2015\-12\-04T00\:00\:00.000Z TO *]'})

        query = handler.parse_query(field, {'query': date(2015, 12, 4), 'range': 'max'})
        self.assertEqual(query, {'fq': r'dummyfield:[* TO 2015\-12\-04T00\:00\:00.000Z]'})

        query = handler.parse_query(field, {
            'query': [date(2015, 12, 4), date(2015, 12, 5)], 'range': 'min:max'})
        self.assertEqual(query, {
            'fq': r'dummyfield:[2015\-12\-04T00\:00\:00.000Z TO 2015\-12\-05T00\:00\:00.000Z]'})


class TextFieldHandlerTests(unittest.TestCase):

    def _getTargetClass(self):
        from alm.solrindex.handlers import TextFieldHandler
        return TextFieldHandler

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

    def test_simple(self):
        field = DummyField()
        field_query = u'alpha beta'
        handler = self._makeOne()
        param = handler.parse_query(field, field_query)
        self.assertEqual(param, {'q': u'+dummyfield:(alpha beta)'})

    def test_complex(self):
        field = DummyField()
        field_query = u'(fun OR play) +with Solr^4'
        handler = self._makeOne()
        param = handler.parse_query(field, field_query)
        self.assertEqual(param,
            {'q': u'+dummyfield:((fun OR play) +with Solr^4)'})


class DummyField:
    name = 'dummyfield'
