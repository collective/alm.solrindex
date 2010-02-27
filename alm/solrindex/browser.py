
from alm.solrindex.index import SolrIndex


class SolrIndexAddView:

    def __call__(self, id='', solr_uri='', submit_add='',
            delete_redundant=False):

        if submit_add and id and solr_uri:
            obj = SolrIndex(id, solr_uri)
            zcatalog = self.context.context
            catalog = zcatalog._catalog
            catalog.addIndex(id, obj)

            zcatalog._p_jar.add(obj)
            cm = obj.connection_manager
            if delete_redundant:
                for field in cm.schema.fields:
                    name = field.name
                    if name != id and catalog.indexes.has_key(name):
                        catalog.delIndex(name)

            self.request.response.redirect(
                zcatalog.absolute_url() +
                "/manage_catalogIndexes?manage_tabs_message=Index%20Added")

        # Note the unfortunate homonym "index": self.index() renders the add
        # form, which submits to this method to add a catalog index.
        return self.index()
