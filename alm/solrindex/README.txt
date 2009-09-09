
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



