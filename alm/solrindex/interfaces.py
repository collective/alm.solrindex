
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
    enable_indexing = Attribute("""
        True to enable indexing operations.  If false, Solr will not
        be changed on catalog updates.
        """)
    enable_querying = Attribute("""
        True to enable querying Solr.  If false, Solr will not be
        consulted for queries.
        """)


class ISolrConnectionManager(Interface):
    """Provides a SolrConnection, schema info, and transaction integration"""
    connection = Attribute("An instance of solr.SolrConnection (from solrpy)")
    schema = Attribute("An ISolrSchema instance")

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
    query_converter = Attribute("An ISolrQueryConverter")


class ISolrQueryConverter(Interface):
    """Convert part of a catalog query to Solr query text.

    The returned text must include a prefix specifying the field name
    to be queried, and some characters must be escaped according to
    Lucene rules. For example, r'SearchableText:"I say \"potato\"\!"'.
    See:

        http://lucene.apache.org/java/2_4_0/queryparsersyntax.html
        http://wiki.apache.org/solr/SolrQuerySyntax

    Register instances providing this interface as utilities.
    Register by field name (most specific), Java class name (less
    specific), or no name (most general).
    """
    def __call__(field, field_query):
        """Covert the field query to Solr query text.

        field is an ISolrField. field_query is the field-specific part
        of the catalog query. Implementations will probably use the
        parseIndexRequest class in Products.PluggableIndexes.common.util
        for handling the various forms that a field query can take.

        The returned query text must be a string or unicode. Before
        passing the query to Solr, the query will be joined with other
        query texts using ' AND '.
        """


class ISolrIndexingWrapper(Interface):
    """Optional wrapper for indexing.

    Just before indexing, the SolrIndex class adapts the object it
    is indexing to this interface.  To fill field values, the SolrIndex
    class pulls attribute values out of the adapter.  If no such adapter
    exists, the SolrIndex pulls attribute values out of the object
    directly.
    """


class ISolrIndexData(Interface):
    """Optional data converter for indexing.

    While indexing, the SolrIndex attempts to adapt every field
    value to this interface.  If an adapter is found, the adapter
    is used in place of the field value.
    """

    def __unicode__():
        """Return the unicode representation of the value.

        The unicode value will be added to an XML document.
        """
