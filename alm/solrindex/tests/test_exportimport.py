from Products.GenericSetup.testing import NodeAdapterTestCase
from Products.GenericSetup.testing import ExportImportZCMLLayer
from Products.Five import zcml
import unittest

_SOLR_URI = 'http://localhost:8988/solr'

_SOLRINDEX_XML = """\
<index name="Solr" meta_type="SolrIndex">
 <property name="solr_uri_static">%s</property>
 <property name="solr_uri_env_var"></property>
 <property name="expected_encodings">
  <element value="utf-8"/>
 </property>
 <property name="catalog_name">portal_catalog</property>
</index>
""" % _SOLR_URI


class SolrExportImportZCMLLayer(ExportImportZCMLLayer):

    @classmethod
    def setUp(cls):
        import alm.solrindex
        ExportImportZCMLLayer.setUp()
        zcml.load_config('configure.zcml', alm.solrindex)


class SolrIndexNodeAdapterTests(NodeAdapterTestCase, unittest.TestCase):

    layer = SolrExportImportZCMLLayer

    def _getTargetClass(self):
        from alm.solrindex.exportimport import SolrIndexNodeAdapter
        return SolrIndexNodeAdapter

    def setUp(self):
        from alm.solrindex.index import SolrIndex
        self._obj = SolrIndex('Solr', _SOLR_URI)
        self._XML = _SOLRINDEX_XML
