

Querying Solr in ZCatalog queries
---------------------------------

The most straightforward way to issue a Solr query through a ZCatalog
containing a SolrIndex is to specify a "solr_params" dictionary in the
ZCatalog query. For example, if you have a SolrIndex installed in
portal_catalog, this call should query Solr::

    results = portal.portal_catalog(solr_params={'q': 'waldo'})

The SolrIndex will issue the query specified in "solr_params" to Solr.
Solr will return a matching list of document IDs and scores. The
document IDs and scores will be passed back to ZCatalog, which will
intersect the document IDs with results from other indexes. ZCatalog
will then return a sorted list of result objects ("brain" objects).

If you need access to the Solr response object, provide a
``solr_callback`` function in the catalog query. When Solr sends its
response, the function will be called with the parsed Solr response
object. The response object conforms with the documentation of the
``solrpy`` package.


Sorting
-------

SolrIndex only provides document IDs and scores, while ZCatalog retains
the reponsibility for sorting the results. To sort the results from a
query involving SolrIndex, use the "sort_on" parameter like you
normally would with ZCatalog.


Field Handlers
--------------

Field handlers serve two functions.  They parse object attributes
for indexing, and they translate field-specific catalog queries to
Solr queries. [...]


Misc notes
----------

Part of the intent of this package is to create a clean division of
responsibilities between ZCatalog and Solr. In this package, it is
expected that an index is either in ZCatalog or Solr, not both. In
collective.solr, the division is less clear because most ZCatalog
indexes have to be duplicated in Solr.





Troubleshooting
---------------

If the Solr index is preventing you from accessing Zope for some reason,
you can set DISABLE_SOLR=YES in the environment, causing the Solr index
to bypass Solr for all queries and updates.



