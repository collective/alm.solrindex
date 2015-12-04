import unittest
from zope.testing.cleanup import cleanUp


class SolrSchemaTests(unittest.TestCase):

    def setUp(self):
        cleanUp()

    def tearDown(self):
        cleanUp()

    def _getTargetClass(self):
        from alm.solrindex.schema import SolrSchema
        return SolrSchema

    def _makeOne(self, solr_uri=None):
        return self._getTargetClass()(solr_uri=solr_uri)

    def test_verifyImplements(self):
        from zope.interface.verify import verifyClass
        from alm.solrindex.interfaces import ISolrSchema
        verifyClass(ISolrSchema, self._getTargetClass())

    def test_verifyProvides(self):
        from zope.interface.verify import verifyObject
        from alm.solrindex.interfaces import ISolrSchema
        verifyObject(ISolrSchema, self._makeOne())

    def test_download_from(self):
        import os
        import shutil
        import tempfile

        schema = self._makeOne()

        d = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(d, 'admin', 'file'))
            fn = os.path.join(d, 'admin', 'file', '?file=schema.xml')
            f = open(fn, 'w')
            f.write('<schema></schema>')
            f.close()
            solr_uri = 'file://%s' % d.replace(os.sep, '/')
            f = schema.download_from(solr_uri)
            content = f.read()
            f.close()
        finally:
            shutil.rmtree(d)

        self.assertEqual(content, '<schema></schema>')

    def test_xml_init(self):
        import os
        from alm.solrindex.interfaces import ISolrFieldHandler
        from zope.component import getGlobalSiteManager
        getGlobalSiteManager().registerUtility(
            DummyFieldHandler(), ISolrFieldHandler)

        schema = self._makeOne()
        fn = os.path.join(os.path.dirname(__file__), 'schema.xml')
        f = open(fn, 'r')
        schema.xml_init(f)
        f.close()
        self.assertEqual(schema.uniqueKey, 'docid')
        self.assertEqual(schema.defaultSearchField, 'default')

        field_names = [field.name for field in schema.fields]
        self.assertEqual(field_names, [
            'docid',
            'Title',
            'physicalPath',
            'physicalDepth',
            'parentPaths',
            'default',
            'Subject',
            'Description',
            'Creator',
            'Date',
            'SearchableText',
            'Type',
            'allowedRolesAndUsers',
            'created',
            'effective',
            'expires',
            'getIcon',
            'getId',
            'modified',
            'portal_type',
            'review_state',
            'is_folderish',
            ])

        self.assertEqual(schema.fields[0].java_class, 'solr.IntField')
        self.assertEqual(schema.fields[0].required, True)
        self.assertEqual(schema.fields[0].multiValued, False)
        self.assertEqual(schema.fields[4].required, False)
        self.assertEqual(schema.fields[4].multiValued, True)


class DummyFieldHandler:
    pass
