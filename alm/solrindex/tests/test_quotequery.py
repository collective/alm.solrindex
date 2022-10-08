# -*- coding: utf-8 -*-

# This is derived from collective.solr.tests.test_query.

import unittest


class QuoteQueryTests(unittest.TestCase):

    def _callFUT(self, s):
        from alm.solrindex.quotequery import quote_query
        return quote_query(s)

    def testQuoting(self):
        quote = self._callFUT
        self.assertEqual(quote(''), '')
        self.assertEqual(quote(' '), '')
        self.assertEqual(quote('foo'), 'foo')
        self.assertEqual(quote('foo '), 'foo')
        self.assertEqual(quote('"foo"'), '"foo"')
        self.assertEqual(quote('"foo'), '\\"foo')
        self.assertEqual(quote('foo"'), 'foo\\"')
        self.assertEqual(quote('foo bar'), '(foo bar)')
        self.assertEqual(quote('"foo bar" bah'), '("foo bar" bah)')
        self.assertEqual(quote('\\['), '\\[')
        self.assertEqual(quote(')'), '\)')
        self.assertEqual(quote('"(foo bar)" bah'), '("\\(foo bar\\)" bah)')
        self.assertEqual(quote('"(foo\\"bar)" bah'), '("\\(foo\\"bar\\)" bah)')
        self.assertEqual(quote('"foo bar"'), '"foo bar"')
        self.assertEqual(quote('"foo bar'), '(\\"foo bar)')
        self.assertEqual(quote('foo bar what?'), '(foo bar what?)')
        self.assertEqual(quote('[]'), '')
        self.assertEqual(quote('()'), '')
        self.assertEqual(quote('{}'), '')
        self.assertEqual(quote('...""'), '...\\"\\"')
        # Search for \ has to be quoted
        self.assertEqual(quote('\\'), '\\\\')
        self.assertEqual(quote('\?'), '\?')
        self.assertEqual(quote('john@foo.com'), 'john@foo.com')
        self.assertEqual(quote(
           'http://machine/folder and item and some/path and and amilli3*'),
           r'(http\://machine/folder and item and some/path and and amilli3*)')
        self.assertEqual(quote('"[]"'), '"\[\]"')
        self.assertEqual(quote('"{}"'), '"\{\}"')
        self.assertEqual(quote('"()"'), '"\(\)"')
        self.assertEqual(
            quote('foo and bar and 42"*'), '(foo and bar and 42\\"\\*)')
        # Can't use ? or * as beginning of new query
        self.assertEqual(quote('"fix and it"*'), '"fix and it"')
        self.assertEqual(quote('"fix and it"?'), '"fix and it"')
        self.assertEqual(quote('foo and bar and [foobar at foo.com]*'),
                               '(foo and bar and \[foobar at foo.com\])')

    def testQuotingWildcardSearches(self):
        quote = self._callFUT
        self.assertEqual(quote('te?t'), 'te?t')
        self.assertEqual(quote('test*'), 'test*')
        self.assertEqual(quote('test**'), 'test*')
        self.assertEqual(quote('te*t'), 'te*t')
        self.assertEqual(quote('?test'), 'test')
        self.assertEqual(quote('*test'), 'test')

    def testQuotingFuzzySearches(self):
        quote = self._callFUT
        self.assertEqual(quote('roam~'), 'roam~')
        self.assertEqual(quote('roam~0.8'), 'roam~0.8')

    def testQuotingProximitySearches(self):
        quote = self._callFUT
        self.assertEqual(quote('"jakarta apache"~10'), '"jakarta apache"~10')

    def testQuotingRangeSearches(self):
        quote = self._callFUT
        self.assertEqual(quote('[* TO NOW]'), '[* TO NOW]')
        self.assertEqual(quote('[1972-05-11T00:00:00.000Z TO *]'),
                               '[1972-05-11T00:00:00.000Z TO *]')
        self.assertEqual(quote(
            '[1972-05-11T00:00:00.000Z TO 2011-05-10T01:30:00.000Z]'),
            '[1972-05-11T00:00:00.000Z TO 2011-05-10T01:30:00.000Z]')
        self.assertEqual(quote('[20020101 TO 20030101]'),
                               '[20020101 TO 20030101]')
        self.assertEqual(quote('{Aida TO Carmen}'), '{Aida TO Carmen}')
        self.assertEqual(quote('{Aida TO}'), '{Aida TO *}')
        self.assertEqual(quote('{TO Carmen}'), '{* TO Carmen}')

    def testQuotingBoostingTerm(self):
        quote = self._callFUT
        self.assertEqual(quote('jakarta^4 apache'), '(jakarta^4 apache)')
        self.assertEqual(quote('jakarta^0.2 apache'), '(jakarta^0.2 apache)')
        self.assertEqual(quote('"jakarta apache"^4 "Apache Lucene"'),
                               '("jakarta apache"^4 "Apache Lucene")')

    def testQuotingOperatorsGrouping(self):
        quote = self._callFUT
        self.assertEqual(quote('+return +"pink panther"'),
                               '(+return +"pink panther")')
        self.assertEqual(quote('+jakarta lucene'), '(+jakarta lucene)')
        self.assertEqual(quote('"jakarta apache" -"Apache Lucene"'),
                               '("jakarta apache" -"Apache Lucene")')
        self.assertEqual(quote('"jakarta apache" NOT "Apache Lucene"'),
                               '("jakarta apache" NOT "Apache Lucene")')
        self.assertEqual(quote('"jakarta apache" OR jakarta'),
                               '("jakarta apache" OR jakarta)')
        self.assertEqual(quote('"jakarta apache" AND "Apache Lucene"'),
                               '("jakarta apache" AND "Apache Lucene")')
        self.assertEqual(quote('(jakarta OR apache) AND website'),
                               '((jakarta OR apache) AND website)')
        self.assertEqual(quote('(a AND (b OR c))'), '(a AND (b OR c))')
        self.assertEqual(quote('((a AND b) OR c)'), '((a AND b) OR c)')

    def testQuotingEscapingSpecialCharacters(self):
        quote = self._callFUT
        self.assertEqual(quote('-+&&||!^~:'), '\\-\\+\\&&\\||\\!\\^\\~\\:')
        # Only quote * and ? if quoted
        self.assertEqual(quote('"*?"'), '"\\*\\?"')

    def testUnicode(self):
        quote = self._callFUT
        self.assertEqual(quote(u'foø'), u'foø')
        self.assertEqual(quote(u'"foø'), u'\\"foø')
        self.assertEqual(quote(u'whät?'), u'whät?')
        self.assertEqual(quote(u'"whät?"'), u'"whät\\?"')
        self.assertEqual(quote(u'"[ø]"'), u'"\\[ø\\]"')
        self.assertEqual(quote(u'[ø]'), u'\\[ø\\]')
        self.assertEqual(quote(u'"foø*"'), u'"foø\\*"')
        self.assertEqual(quote(u'"foø bar?"'), u'"foø bar\\?"')
        self.assertEqual(quote(u'john@foo.com'), u'john@foo.com')

    def testSolrSpecifics(self):
        # http://wiki.apache.org/solr/SolrQuerySyntax
        quote = self._callFUT
        self.assertEqual(
            quote('"recip(rord(myfield),1,2,3)"'),
            r'"recip\(rord\(myfield\),1,2,3\)"')
             # Seems to be ok to quote function
        self.assertEqual(quote('[* TO NOW]'), '[* TO NOW]')
        self.assertEqual(quote(
            '[1976-03-06T23:59:59.999Z TO *]'),
            '[1976-03-06T23:59:59.999Z TO *]')
        self.assertEqual(quote(
            '[1995-12-31T23:59:59.999Z TO 2007-03-06T00:00:00Z]'),
            '[1995-12-31T23:59:59.999Z TO 2007-03-06T00:00:00Z]')
        self.assertEqual(quote(
            '[NOW-1YEAR/DAY TO NOW/DAY+1DAY]'),
            '[NOW-1YEAR/DAY TO NOW/DAY+1DAY]')
        self.assertEqual(quote(
            '[1976-03-06T23:59:59.999Z TO 1976-03-06T23:59:59.999Z+1YEAR]'),
            '[1976-03-06T23:59:59.999Z TO 1976-03-06T23:59:59.999Z+1YEAR]')
        self.assertEqual(quote(
            '[1976-03-06T23:59:59.999Z/YEAR TO 1976-03-06T23:59:59.999Z]'),
            '[1976-03-06T23:59:59.999Z/YEAR TO 1976-03-06T23:59:59.999Z]')

    def test_special_character_not_in_operator(self):
        quote = self._callFUT
        self.assertEqual(quote('ham&eggs'), 'ham&eggs')
        self.assertEqual(quote('ls -l | less'), '(ls -l | less)')
