
import Globals  # import Zope 2 dependencies in order

from alm.solrindex.interfaces import ISolrQueryConverter
from Products.PluginIndexes.common.util import parseIndexRequest
from zope.interface import implements
import re

# See: http://lucene.apache.org/java/2_4_0/queryparsersyntax.html
_escape_chars = re.compile(r'([-+&|!(){}\[\]^"~*?:\\])')

def solr_escape(query):
    return _escape_chars.sub(r'\\\1', query)


class DefaultQueryConverter(object):
    implements(ISolrQueryConverter)

    def __call__(self, field, field_query):
        name = field.name
        request = {name: field_query}
        record = parseIndexRequest(request, name, ('query',))
        if record.keys is None:
            return None
        query_str = ' '.join(record.keys)
        if not query_str:
            return None

        if not isinstance(query_str, unicode):
            query_str = unicode(query_str, 'utf-8')
        escaped = solr_escape(query_str)

        return '%s:"%s"' % (name, escaped)
