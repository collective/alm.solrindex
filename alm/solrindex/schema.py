
"""Parser of a Solr schema.xml"""

from alm.solrindex.interfaces import ISolrField
from alm.solrindex.interfaces import ISolrFieldHandler
from alm.solrindex.interfaces import ISolrSchema
try:
    from elementtree.ElementTree import parse
except ImportError:
    from lxml.etree import parse

from zope.component import getUtility
from zope.component import queryUtility
from zope.interface import implements
import logging
import urllib2

log = logging.getLogger(__name__)


class SolrSchema(object):
    implements(ISolrSchema)

    uniqueKey = None
    defaultSearchField = None

    def __init__(self, solr_uri=None):
        self.fields = []
        if solr_uri:
            f = self.download_from(solr_uri)
            try:
                self.xml_init(f)
            finally:
                f.close()

    def download_from(self, solr_uri):
        """Get schema.xml from a running Solr instance"""
        schema_uris = ('%s/admin/file/?file=schema.xml',         # solr 1.3
                       '%s/admin/get-file.jsp?file=schema.xml')  # solr 1.2
        for i, uri in enumerate(schema_uris):
            uri = uri % solr_uri
            log.debug('getting schema from %s', uri)
            try:
                f = urllib2.urlopen(uri)
            except urllib2.URLError:
                if i < len(schema_uris) - 1:
                    # try the next URI
                    continue
                raise
            return f

    def xml_init(self, f):
        """Initialize this instance from a Solr schema.xml"""
        tree = parse(f)

        e = tree.find('uniqueKey')
        if e is not None:
            self.uniqueKey = e.text.strip()

        e = tree.find('defaultSearchField')
        if e is not None:
            self.defaultSearchField = e.text.strip()

        types = {}
        for e in tree.findall('types/fieldType'):
            types[e.attrib['name']] = e

        for e in tree.findall('fields/field'):
            t = types[e.attrib['type']]
            self.fields.append(SolrField(e, t))


class SolrField(object):
    implements(ISolrField)

    _boolean_attrs = (
        'indexed', 'stored', 'required', 'multiValued',
        )

    def __init__(self, elem, fieldType):
        self.name = elem.attrib['name']
        self.type = elem.attrib['type']
        self.java_class = fieldType.attrib['class']
        for attr in self._boolean_attrs:
            value = elem.get(attr)
            if value is not None:
                value = {'true': True, 'false': False}[value.lower()]
            setattr(self, attr, value)

        handler = queryUtility(ISolrFieldHandler, name=self.name)
        if handler is None:
            handler = queryUtility(
                ISolrFieldHandler, name=self.java_class)
            if handler is None:
                handler = getUtility(ISolrFieldHandler)
        self.handler = handler
