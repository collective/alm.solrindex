

This is an experimental module that provides a simple catalog index
using Solr.  It works fine, but more thought needs to be put into it.
For example, it needs query munging, load testing, and more Solr
features.

To enable it as-is:

- Include this package in a configure.zcml.

- Add the dependency "solrpy" to setup.py.

- In schema.xml:

    - Change the Solr schema to only have the fields "docid" and
      "SearchableText".

    - Set the uniqueKey to "docid".

    - Make SearchableText the default field.

    - Comment out the copyField directives.

