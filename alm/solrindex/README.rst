
Installation
------------

Include this package in your Zope 2 or Plone buildout. If you are using
the ``plone.recipe.zope2instance`` recipe, add ``alm.solrindex`` to the
``eggs`` parameter and the ``zcml`` parameter. See the ``buildout.cfg``
in this package for an example. The example also shows how to use the
``collective.recipe.solrinstance`` recipe to build a working Solr
instance with little extra effort.

Once Zope is running with this package installed, you can visit a
ZCatalog and add ``SolrIndex`` as an index. You should only add one
SolrIndex to a ZCatalog, but a single SolrIndex can take the place of
multiple ZCatalog indexes.


The Solr Schema
---------------

Configure the Solr schema to store an integer unique key.  Add fields
with names matching the attributes of objects you want to index in Solr.
You should avoid creating a Solr field that will index the same data
as what will be indexed in ZODB by another ZCatalog index.  In other
words, if you add a ``Description`` field to Solr, you probably ought
to remove the index named ``Description`` from ZCatalog, so that you
don't force your system to index descriptions twice.

Once the SolrIndex is installed, you can query all of the fields
described by the Solr schema, even if there is no ZCatalog index with
a matching name.  For example, if you have configured a ``Description``
field in the Solr schema, then you can issue catalog queries against
the ``Description`` field using the same syntax you would use with
other ZCatalog indexes.  For example::

    results = portal.portal_catalog(Description={'query': 'waldo'})

Queries of this form pass through a configurable translation layer made
of field handler objects. When you need more flexibility than the field
handlers provide, you can either write your own field handlers (see the
"Writing Your Own Field Handlers" section) or you can provide Solr
parameters that do not get translated (see the "Translucent Solr
Queries" section).


Translucent Solr Queries
------------------------

You can issue a Solr query through a ZCatalog containing a SolrIndex by
providing a ``solr_params`` dictionary in the ZCatalog query. For
example, if you have a SolrIndex installed in portal_catalog, this call
will query Solr::

    results = portal.portal_catalog(solr_params={'q': 'waldo'})

The SolrIndex in the catalog will issue the query parameters specified
in ``solr_params`` to Solr. Each parameter value can be a string
(including unicode) or a list of strings. If you provide query
parameters for other Solr fields, the parameters passed to Solr will be
mixed with parameters generated for the other fields.  Note that Solr
requires some value for the '``q``' parameter, so if you provide Solr
parameters but no value for '``q``', SolrIndex will supply '``*:*``' as the
value for '``q``'.

Solr will return to the SolrIndex a list of matching document IDs and
scores, then the SolrIndex will pass the document IDs and scores to
ZCatalog, then ZCatalog will intersect the document IDs with results
from other indexes. Finally, ZCatalog will return a sorted list of
result objects ("brain" objects) to application code.

If you need access to the Solr response object, provide a
``solr_callback`` function in the catalog query. After Solr sends its
response, the SolrIndex will call the callback function with the parsed
Solr response object. The response object conforms with the
documentation of the ``solrpy`` package.


Highlighting
------------

Highlighting data may be requested for any field marked as ``stored``
in the Solr schema. To enable this feature, pass a ``highlight`` value of
either ``True``, or a list of field names to highlight. A value of ``queried``
will cause Solr to return highlighting data for the list of queried columns.
If you pass in a sequence of field names, the requested highlighting data
will be limited to that list. You can also enable it by default in your Solr
config file. If you do enable it by default in the config file, but don't
want it for a particular query, you must pass ``hl``:``off`` in solr_params.

The retrieved data is stored in the ``highlighting`` attribute on the
returned brain. To use the custom ``HighlightingBrain``, the index needs to
be able to connect to its parent catalog. The code attempts to retrieve a
named utility for this, and will attempt to use Acquisition to find the id
of its immediate parent. Failing that, it defaults to using ``portal_catalog``.
If the code cannot determine the name of your catalog automatically and you
want to use highlighting, you will need to change the ``catalog_name``
property of the SolrIndex to reflect the correct value.

To retrieve the highlighting data, the brain will have a ``getHighlighting``
method. By default, this is set to return the highlighting data for all
fields in a single list. You can limit this to specific fields, and change
the return format to a dictionary keyed on field name by passing
``combine_fields=False``.

Example:

    results = portal.portal_catalog(SearchableText='lincoln',
                                    solr_params={'highlight': True})
    
    results[0].getHighlighting()
    [u'<em>lincoln</em>-collections  <em>Lincoln</em> ',
    u'The collection of <em>Lincoln</em> plates']
    
    results[0].getHighlighting(combine_fields=False)
    {'SearchableText': [u'<em>lincoln</em>-collections  <em>Lincoln</em> ']}
    'Description': [u'The collection of <em>Lincoln</em> plates']}
    
    results[0].getHighlighting('Description')
    [u'The collection of <em>Lincoln</em> plates']
    
    results[0].getHighlighting('Description', combine_fields=False)
    {'Description': [u'The collection of <em>Lincoln</em> plates']}

The number of snippets returned, how the search terms are highlighted, and
several other settings can all be tweaked in your Solr config.

http://wiki.apache.org/solr/HighlightingParameters


Encoding
--------

All data submitted to Solr for indexing or as a query must be encoded as
UTF-8. To this end, the SolrIndex has an ``expected_encodings`` lines
property that details the list of encodings for it to try to decode data
from before transcoding to UTF-8. If you submit data to be indexed or
queries with strings in a different encoding, you need to add that
encoding to this list, before UTF-8.

http://wiki.apache.org/solr/FAQ#Why_don.27t_International_Characters_Work.3F


Sorting
-------

SolrIndex only provides document IDs and scores, while ZCatalog retains
the responsibility for sorting the results. To sort the results from a
query involving SolrIndex, use the ``sort_on`` parameter like you
normally would with ZCatalog. At this time, you can not use a SolrIndex
as the index to sort on, but that could change in the future.


Writing Your Own Field Handlers
-------------------------------

Field handlers serve two functions. They parse object attributes for
indexing, and they translate field-specific catalog queries to Solr
queries. They are registered as utilities, so you can write your own
handlers and register them using ZCML.

To determine the field handler for a Solr field, ``alm.solrindex`` first
looks for an ``ISolrFieldHandler`` utility with a name matching the field
name. If it doesn't find one, it looks for an ``ISolrFieldHandler`` utility
with a name matching the name of the Java class that handles the field
in Solr. If that also fails, it retrieves the ``ISolrFieldHandler`` with no
name.

See the documentation of the ``ISolrFieldHandler`` interface and the examples
in handlers.py.


Integration with ZCatalog
-------------------------

One ``SolrIndex`` can take the place of several ZCatalog indexes. In
theory, you could replace all of the catalog indexes with just a single
``SolrIndex``. Don't do that yet, though, because this package needs
more maturity before it's ready to take on that many responsibilities.

Furthermore, replacing all ZCatalog indexes might not be the right
goal. ZCatalog indexes are under appreciated. ZCatalog indexes are built
on the excellent transaction-aware object cache provided by ZODB. This
gives them certain inherent performance advantages over network bound
search engines like Solr. Any communication with Solr incurs a delay on
the order of a millisecond, while a ZCatalog index can often answer a
query in a few microseconds. ZCatalog indexes also simplify cluster
design. The ZODB cache allows cluster nodes to perform searches without
relying on a large central search engine.

Where ZCatalog indexes currently fall short, however, is in the realm
of indexing text. None of the text indexes available for ZCatalog match
the features and performance of text search engines like Solr.

Therefore, one good way to use this package is to move all text indexes
to Solr. That way, queries that don't need the text engine will avoid
the expense of invoking Solr. You can also move other kinds of indexes
to Solr.


How This Package Maintains Persistent Connections
-------------------------------------------------

This package uses a new method of maintaining an external database
connection from a ZODB object. Previous approaches included storing
``_v_`` (volatile) attributes, keeping connections in a thread local
variable, and reusing the multi-database support inside ZODB, but
those approaches each have significant drawbacks.

The new method is to add dictionary called ``foreign_connections`` to
the ZODB Connection object (the ``_p_jar`` attribute of any persisted
object). Each key in the dictionary is the OID of the object that needs
to maintain a persistent connection. Each value is an
implementation-dependent database connection or connection wrapper. If
it is possible to write to the external database, the database
connection or connection wrapper should implement the ``IDataManager``
interface so that it can be included in transaction commit or abort.

When a SolrIndex needs a connection to Solr, it first looks in the
``foreign_connections`` dictionary to see if a connection has already
been made. If no connection has been made, the SolrIndex makes the
connection immediately. Each ZODB connection has its own
``foreign_connections`` attribute, so database connections are not
shared by concurrent threads, making this a thread safe solution.

This solution is better than ``_v_`` attributes because connections will
not be dropped due to ordinary object deactivation. This solution is
better than thread local variables because it allows the object
database to hold any number of external connections and it does not
break when you pass control between threads. This solution is better
than using multi-database support because participants in a
multi-database are required to fulfill a complex contract that is
irrelevant to databases other than ZODB.

Other packages that maintain an external database connection should try
out this scheme to see if it improves reliability or readability. Other
packages should use the same ZODB Connection attribute name,
``foreign_connections``, which should not cause any clashes, since
OIDs can not be shared.

An implementation note: when ZODB objects are first created, they are
not stored in any database, so there is no simple way for the object to
get a ``foreign_connections`` dictionary. During that time, one way to hold
a database connection is to temporarily fall back to the volatile
attribute solution. That is what SolrIndex does (see the ``_v_temp_cm``
attribute).


Troubleshooting
---------------

If the Solr index is preventing you from accessing Zope for some reason,
you can set ``DISABLE_SOLR=YES`` in the environment, causing the SolrIndex
class to bypass Solr for all queries and updates.

