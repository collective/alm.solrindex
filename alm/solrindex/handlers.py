
import Globals  # import Zope 2 dependencies in order

from alm.solrindex.interfaces import ISolrFieldHandler
from Products.PluginIndexes.common.util import parseIndexRequest
from zope.interface import implements
import re
import time
from datetime import date, datetime
from DateTime.DateTime import DateTime

# See: http://lucene.apache.org/java/2_4_0/queryparsersyntax.html
_escape_chars = re.compile(r'([-+&|!(){}\[\]^"~*?:\\])')

def solr_escape(query):
    return _escape_chars.sub(r'\\\1', query)


class DefaultFieldHandler(object):
    implements(ISolrFieldHandler)

    def parse_query(self, field, field_query):
        name = field.name
        request = {name: field_query}
        record = parseIndexRequest(request, name, ('query',))
        if not record.keys:
            return None

        parts = []
        for part in record.keys:
            part = self.convert(part)
            if part:
                parts.append(part)
        query_str = u' '.join(parts)
        if not query_str:
            return None

        escaped = solr_escape(query_str)
        return u'%s:"%s"' % (name, escaped)

    def convert(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            return unicode(value, 'utf-8')
        return unicode(value)


class DateFieldHandler(DefaultFieldHandler):

    # TODO: try to match the query capabilities of PluginIndexes.DateIndex.

    def convert(self, value):
        if value is None:
            return None

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
