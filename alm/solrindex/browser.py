
from alm.solrindex.index import SolrIndex

class SolrIndexAddView:

    def __call__(self, id='', solr_uri='', submit_add=''):
        if submit_add and id and solr_uri:
            obj = SolrIndex(id, solr_uri)
            zcatalog = self.context.context
            zcatalog._catalog.addIndex(id, obj)
            self.request.response.redirect(
                zcatalog.absolute_url() +
                "/manage_catalogIndexes?manage_tabs_message=Index%20Added")

        # Note the unfortunate homonym "index": self.index() renders the add
        # form, which submits to this method to add a catalog index.
        return self.index()
