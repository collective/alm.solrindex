from __future__ import unicode_literals
from Products.GenericSetup.interfaces import INode
from Products.GenericSetup.testing import NodeAdapterTestCase
from Products.GenericSetup.testing import DummySetupEnviron
from Products.GenericSetup.testing import ExportImportZCMLLayer
from xml.dom.minidom import parseString
from Zope2.App import zcml
from zope.component import getMultiAdapter
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
        import alm.solrindex
        from alm.solrindex.index import SolrIndex
        # Needed to make tests work on Plone 5.2
        # Might not be the right approach: I'm no expert
        ExportImportZCMLLayer.setUp()
        zcml.load_config('configure.zcml', alm.solrindex)

        self._obj = SolrIndex('Solr', _SOLR_URI)
        self._XML = _SOLRINDEX_XML

    def test_node_get(self):
        self._populate(self._obj)
        context = DummySetupEnviron()
        adapted = getMultiAdapter((self._obj, context), INode)
        self.assertEqual(adapted.node.toprettyxml(" "), self._XML)

    def test_node_set(self):
        context = DummySetupEnviron()
        adapted = getMultiAdapter((self._obj, context), INode)
        adapted.node = parseString(self._XML).documentElement
        self._verifyImport(self._obj)
        self.assertEqual(adapted.node.toprettyxml(" "), self._XML)

        # now in update mode
        context._should_purge = False
        adapted = getMultiAdapter((self._obj, context), INode)
        adapted.node = parseString(self._XML).documentElement
        self._verifyImport(self._obj)
        self.assertEqual(adapted.node.toprettyxml(" "), self._XML)

        # and again in update mode
        adapted = getMultiAdapter((self._obj, context), INode)
        adapted.node = parseString(self._XML).documentElement
        self._verifyImport(self._obj)
        self.assertEqual(adapted.node.toprettyxml(" "), self._XML)
