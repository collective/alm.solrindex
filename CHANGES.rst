Changelog
=========

1.2.0 (2016-10-15)
------------------

- Fix typo in solrpycore.
  [davidblewett]

- Thanks to: "Schorr, Dr. Thomas" <thomas.schorr@haufe.de> for the following
  encoding fixes, refs ticket #1:

  - Added a `expected_encodings` property to `SolrIndex` that lists the encodings
    to expect text in; each is tried in turn to decode each parameter sent to
    Solr. If none succeeds in decoding the text, we fall back to UTF8 and replace
    failing characters.
    http://wiki.apache.org/solr/FAQ#Why_don.27t_International_Characters_Work.3F
    [davidblewett]

  - Added `_encode_param` method to `SolrIndex` to encode a given string to UTF8.
    [davidblewett]

  - Modified `SolrIndex`'s '_apply_index` to send all parameters through the
    `_encode_param` method.
    [davidblewett]

  - Added a `test__apply_index_with_unicode` to ensure unicode queries are
    handled correctly.
    [davidblewett]

- Initial highlighting support:

  - Imported `getToolByName` from `Products.CMFCore`, to be used on import failure.
  - Updated `SolrIndex` to pass any fields from the Solr schema that have stored=True to be highlighted.
  - Updated `SolrIndex` to store highlighting data returned from Solr in a `_highlighting` attribute.
  - Added a `HighlightingBrain` class that subclasses `AbstractCatalogBrain` that looks up the highlighted data in `SolrIndex`.
  - Added a `test__apply_index_with_highlighting` test; unfortunately, calling the `portal_catalog`
    is not working in the tests currently.

  [davidblewett]

- Fixed : IIBTree needs integer keys
  http://plone.org/products/alm.solrindex/issues/3
  [thomasdesvenain]

- Quick Plone 4 compatibility fixes
  [thomasdesvenain]

- Search using ZCTextIndex '*' key character works with alm.solrindex.
  Makes livesearch works with solrindex as SearchableText index.
  [thomasdesvenain]

- Highlighting is not activated by default because there can be severe performance issues.
  Pass 'highlight' parameter in solr_params to force it,
  and pass 'queried' as 'highlight' value to force highlight on queried fields only.
  [thomasdesvenain]

- Improved unicode handling to correctly handle dictionaries passed in as a field search,
  in `SolrIndex._decode_param`.
  [davidblewett]

- Extended ZCTextIndex support when a dictionary is passed in as a field search.
  [davidblewett]

- Update test setup so that it is testing against Solr 1.4
  [claytron]

- Handle empty ``dismax`` queries since a ``*:*`` value for ``q`` is not
  interpreted for the ``dismax`` query handler and returns no results
  rather than all results.
  [claytron]

- Add uninstall profile, restoring the default Plone indizes.
  [thet]

- Give the SolrIndex a meta_type 'SolrIndex' and register
  ATSimpleStringCriterion for it, otherwise Collections cannot add
  SearchableText criteria.
  [maurits]

- Ensure that only one 'q' parameter is sent to Solr.
  [claytron]

- Plone 4.1 compatibility.
  [timo]

- Add missing elementtree import
  [saily]

- Fix stale cached highlighting information that 
  lead to in inconsistent results.
  [nrb]

- Plone 4.3 compatibility.
  [cguardia]

- Add support for solr.TrieDateField
  [mjpieters]

- Fix decoding of query requests so that lists are not stringified
  before getting sent to field handlers.
  [davisagli]

- Implement getIndexQueryNames which is now part of IPluggableIndex.
  [davisagli]

- Add support for range queries to the DateFieldHandler.
  [davisagli]

- Don't turn wildcard queries into fuzzy queries.
  [davisagli]

- Confirm compatibility with Plone 5
  [witekdev, davisagli]


1.1.1 (2010-11-04)
------------------

- Fix up links to issue tracker and Plone product page
  [clayton]

1.1 (2010-10-12)
----------------

- Added `z3c.autoinclude` support for Plone
  [claytron]

1.0 (2010-05-27)
----------------

- Initial public release

- Clean up docs in prep for release.
  [claytron]

- Fix up reST errors.
  [claytron]

0.14 (2010-05-11)
-----------------

- Updated SolrConnectionManager to have a dummy savepoint
  implementation, refs #2451.
  [davidb]

0.13 (2010-03-01)
-----------------

- commit to cleanup version #'s

0.12 (2010-03-01)
-----------------

- PEP8 cleanup
  [clayton]

0.11 (2009-11-27)
-----------------

- A commit after an aborted index update no longer breaks with an
  assertion error.  Refs #1340

0.10 (2009-10-15)
-----------------

- Filter out invalid XML characters from indexed documents.

0.9 (2009-10-14)
----------------

- Fixed test failure by going to the login_form to log in, instead of
  the front page, where we get ambiguity errors.
  [maurits]

- Fixed the catalog object information page.  Solr was unable to parse
  a negative number in the query.


0.8 (2009-09-18)
----------------

- Added support for Solr boolean fields.

- GenericSetup profiles now have the option of clearing the
  index.

- Made the waituri script wait up to 90 seconds by default,
  pause a little more between polls, and accept a timeout
  parameter.

0.7 (2009-09-13)
----------------

- The Solr URI can now be provided by an environment variable,
  so that catalog.xml does not need to hard code the URI.

0.6 (2009-09-11)
----------------

- Added narrative documentation.

- Don't clear the index when running GenericSetup.  Clearing
  indexes turns out to be a long-standing problem with GenericSetup;
  in this case the easy solution is to just not clear it.

0.5 (2009-09-10)
----------------

- Added a script that waits for Solr to start up.

- Brought in a private copy of solrpy to fix some bugs:

  - The connection retry code reconnected, but wasn't
    actually retrying the request.

  - The raw_query method should not assume the parameter
    values are unicode (they could be lists of unicode).

0.4 (2009-09-10)
----------------

- Purge Solr when importing a SolrIndex via GenericSetup.

0.3 (2009-09-10)
----------------

- Made field handlers more flexible.  Now they can add any
  kind of query parameter to the Solr query.

- The default field handler now generates "fq" parameters
  instead of "q" parameters.  This seems to fit the intent of
  the Solr authors much better.

- Renamed "solr_additional" to "solr_params".

0.2 (2009-09-09)
----------------

- Added a GenericSetup profile that replaces SearchableText
  with a SolrIndex.

- Renamed the catalog parameter for passing extra args to Solr
  "solr_additional".  Also renamed the response callback
  parameter to "solr_callback".

0.1 (2009-09-09)
----------------

- First release
