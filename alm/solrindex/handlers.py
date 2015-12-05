
"""Handlers for various Solr field types"""

import Globals  # import Zope 2 dependencies in order

from alm.solrindex.interfaces import ISolrFieldHandler
from alm.solrindex.quotequery import quote_query
from Products.PluginIndexes.common.util import parseIndexRequest
from zope.interface import implements
import re
import time
from datetime import date, datetime
from DateTime.DateTime import DateTime

# See: http://lucene.apache.org/java/2_4_0/queryparsersyntax.html
_escape_chars = re.compile(r'([-+&|!(){}\[\]^"~*?:\\])')

invalid_xml_re = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F]')


def solr_escape(query):
    """Escape all characters that have a special meaning to Solr"""
    return _escape_chars.sub(r'\\\1', query)


class DefaultFieldHandler(object):
    implements(ISolrFieldHandler)

    operators = ('and', 'or')
    default_operator = 'or'

    def parse_query(self, field, field_query):
        name = field.name
        request = {name: field_query}
        record = parseIndexRequest(request, name, ('query', 'operator'))
        if not record.keys:
            return None

        parts = []
        for part in record.keys:
            parts.extend(self.convert(part))
        if not parts:
            return None

        if len(parts) == 1:
            escaped = solr_escape(parts[0])
            return {'fq': u'%s:"%s"' % (name, escaped)}

        operator = record.get('operator', self.default_operator)
        if operator not in self.operators:
            raise AssertionError("Invalid operator: %s" % operator)

        parts_fmt = [u'"%s"' % solr_escape(part) for part in parts]
        s = (u' %s ' % operator.upper()).join(parts_fmt)
        return {'fq': u'%s:(%s)' % (name, s)}

    def convert(self, data):
        if data is None:
            return ()
        if hasattr(data, '__iter__') and not isinstance(data, basestring):
            data_seq = data
        else:
            data_seq = [data]
        res = [self.convert_one(value) for value in data_seq]
        return res

    def convert_one(self, value):
        if isinstance(value, str):
            s = value.decode('utf-8')
        else:
            s = unicode(value)
        return invalid_xml_re.sub('', s)


class BoolFieldHandler(DefaultFieldHandler):

    def convert_one(self, value):
        if value:
            return 'true'
        else:
            return 'false'


class DateFieldHandler(DefaultFieldHandler):

    def parse_query(self, field, field_query):
        name = field.name
        request = {name: field_query}
        record = parseIndexRequest(request, name, ('query', 'range'))
        if not record.keys:
            return None

        query_range = record.get('range', None)
        if query_range is None:
            return super(DateFieldHandler, self).parse_query(field, field_query)
        elif query_range == 'min':
            min_query = self.convert_one(min(record.keys))
            return {'fq': u'%s:[%s TO *]' % (name, solr_escape(min_query))}
        elif query_range == 'max':
            max_query = self.convert_one(max(record.keys))
            return {'fq': u'%s:[* TO %s]' % (name, solr_escape(max_query))}
        elif query_range == 'min:max':
            min_query = self.convert_one(min(record.keys))
            max_query = self.convert_one(max(record.keys))
            return {'fq': u'%s:[%s TO %s]' % (name, solr_escape(min_query), solr_escape(max_query))}
        else:
            raise AssertionError("Invalid range: %s" % range)

    def convert_one(self, value):
        if isinstance(value, DateTime):
            t_tup = value.toZone('UTC').parts()
        elif isinstance(value, (float, int, long)):
            t_tup = time.gmtime(value)
        elif isinstance(value, basestring):
            t_obj = DateTime(value).toZone('UTC')
            t_tup = t_obj.parts()
        elif isinstance(value, date):
            t_tup = value.timetuple()
        elif isinstance(value, datetime):
            t_tup = value.utctimetuple()
        else:
            # can't interpret
            raise TypeError("Not a date value: %s" % repr(value))

        converted = '%04d-%02d-%02dT%02d:%02d:%06.3fZ' % t_tup[:6]
        return converted


class TextFieldHandler(DefaultFieldHandler):

    def parse_query(self, field, field_query):
        name = field.name
        request = {name: field_query}
        record = parseIndexRequest(request, name, ('query',))
        if not record.keys:
            return None

        query_str = ' '.join(record.keys)
        if not query_str:
            return None

        return {'q': u'+%s:%s' % (name, quote_query(query_str))}

    def convert(self, data):
        if data is None:
            return ()
        if hasattr(data, '__iter__') and not isinstance(data, basestring):
            data_seq = data
        else:
            data_seq = [data]
        res = [self.convert_one(value) for value in data_seq]
        return [" ".join(res)]
