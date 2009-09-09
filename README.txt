
alm.solrindex
=============

Introduction
------------

This package is another approach to integrate the `Solr`_ search engine
in `Plone`_.  It is similar to `collective.solr`_, but the method
of integration is simpler and thus easier to understand and maintain.

  .. _`collective.solr`: http://plone.org/products/collective.solr/
  .. _`Solr`: http://lucene.apache.org/solr/
  .. _`Plone`: http://www.plone.org/

This package provides a Solr-based ZCatalog index that can be installed
into any ZCatalog (even outside Plone).  The index will keep Solr up to
date and filter catalog results using Solr queries.
