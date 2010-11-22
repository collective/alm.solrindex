
import Globals  # import Zope 2 dependencies in order

from zope.interface import Attribute
from zope.interface import Interface
from Products.PluginIndexes.interfaces import IPluggableIndex


class ISolrIndex(IPluggableIndex):
    """A ZCatalog multi-index that uses Solr for storage and queries."""
    solr_uri = Attribute("The URI of the Solr server")
    connection_manager = Attribute("""
        An ISolrConnectionManager that is specific to the ZODB connection.
        """)
    expected_encodings = Attribute(
        "List of encodings to try to transcode to UTF8 from when querying Solr"
    )


class ISolrConnectionManager(Interface):
    """Provides a SolrConnection, schema info, and transaction integration.

    An instance of this class gets stored in the foreign_connections
    attribute of a ZODB connection.
    """
    connection = Attribute("An instance of solr.SolrConnection (from solrpy)")
    schema = Attribute("An ISolrSchema instance")
    solr_uri = Attribute("The URI of the Solr server")

    def set_changed():
        """Adds the Solr connection to the current transaction.

        Call this before sending change requests to Solr.
        """


class ISolrSchema(Interface):
    """The relevant part of the schema installed in a Solr instance.
    """
    uniqueKey = Attribute("The name of the unique field")
    defaultSearchField = Attribute("""
        The name of the field to search when no field has been
        specified in the query
        """)
    fields = Attribute("A sequence of ISolrField")


class ISolrField(Interface):
    """A field in Solr"""
    name = Attribute("The name")
    type = Attribute("The type (an arbitrary string; don't rely on it)")
    java_class = Attribute("""
        The fully qualified name of the Java class that handles the field
        """)
    indexed = Attribute("True if the field is searchable")
    stored = Attribute("True if the value of the field can be retrieved")
    required = Attribute("True if a value is required for indexing")
    multiValued = Attribute("True if the field supports multiple values")
    handler = Attribute("An ISolrFieldHandler")


class ISolrFieldHandler(Interface):
    """Adjust field input to fit Solr.

    Register instances providing this interface as utilities.
    Register by field name (most specific), Java class name (less
    specific), or no name (most general).
    """
    def parse_query(field, field_query):
        """Convert a field-specific part of a catalog query to Solr parameters.

        field is an ISolrField. field_query is the field-specific part
        of the catalog query. Most implementations should extend
        DefaultFieldHandler.

        If the field query actually contains nothing to constrain the
        search, this method should return None.

        Return a mapping containing parameters to add to the request.
        Each parameter value in the returned mapping must be either a
        string or a sequence of strings. Note that Solr accepts a list
        of values for every parameter, so SolrIndex will simply pass to
        Solr all of the parameter values provided by every field
        handler.

        Most parameter values should include a prefix specifying the
        field name to be queried, and some characters must be escaped
        according to Lucene rules. See:

            http://lucene.apache.org/java/2_4_0/queryparsersyntax.html
            http://wiki.apache.org/solr/SolrQuerySyntax

        The returned query text must be a string or unicode. Before
        passing the query to Solr, SolrIndex will join the query with
        other query texts using ' AND '.
        """

    def convert(value):
        """Convert a field value to a list of unicode objects for Solr.

        Return a list or tuple of unicode objects (or objects that have
        a __unicode__ or __str__ method).  If there is no data,
        return an empty list or tuple.
        """


class ISolrIndexingWrapper(Interface):
    """Optional wrapper for indexing.

    Just before indexing, the SolrIndex class adapts the object it
    is indexing to this interface.  To fill field values, the SolrIndex
    class pulls attribute values out of the adapter.  If no such adapter
    exists, the SolrIndex pulls attribute values out of the object
    directly.
    """
