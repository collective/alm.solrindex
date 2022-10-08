"""SolrIndex and SolrConnectionManager"""
from Acquisition import aq_parent
from alm.solrindex.interfaces import ISolrConnectionManager
from alm.solrindex.interfaces import ISolrIndex
from alm.solrindex.interfaces import ISolrIndexingWrapper
from alm.solrindex.schema import SolrSchema
from alm.solrindex.solrpycore import SolrConnection
from BTrees.IIBTree import IIBTree
from OFS.PropertyManager import PropertyManager
from OFS.SimpleItem import SimpleItem
from plone.app.textfield.value import RichTextValue
from Products.CMFCore.utils import getToolByName
from Products.ZCatalog.CatalogBrains import AbstractCatalogBrain
from transaction.interfaces import IDataManager
from zope.component import queryAdapter
from zope.interface import implementer

import logging
import os
import transaction


disable_solr = os.environ.get("DISABLE_SOLR")

log = logging.getLogger(__name__)


@implementer(ISolrIndex)
class SolrIndex(PropertyManager, SimpleItem):

    meta_type = "SolrIndex"

    _properties = (
        {
            "id": "solr_uri_static",
            "type": "string",
            "mode": "w",
            "description": 'The Solr URI, for example, "http://localhost:8983/solr". '
            "You should leave this empty if you set solr_uri_env_var.",
        },
        {
            "id": "solr_uri_env_var",
            "type": "string",
            "mode": "w",
            "description": "The name of an environment variable that will provide "
            "the Solr URI.  Ignored if solr_uri_static is non-empty.",
        },
        {
            "id": "solr_uri",
            "type": "string",
            "mode": "",
            "description": "The effective Solr URI (read-only)",
        },
        {
            "id": "expected_encodings",
            "type": "lines",
            "mode": "w",
            "description": "The list of encodings to try to decode in the query"
        },
        {
            "id": "catalog_name",
            "type": "string",
            "mode": "w",
            "description": "The name of the catalog this index is attached to.",
        },
    )

    manage_options = PropertyManager.manage_options + SimpleItem.manage_options

    _v_temp_cm = None  # An ISolrConnectionManager used during initialization
    solr_uri_static = ""
    solr_uri_env_var = ""
    expected_encodings = ["utf-8"]
    catalog_name = "portal_catalog"

    def __init__(
        self, id, solr_uri_static="", expected_encodings=None, catalog_name=None
    ):
        self.id = id
        self.solr_uri_static = solr_uri_static
        if expected_encodings is not None:
            self.expected_encodings = expected_encodings
        if catalog_name is None:
            parent = aq_parent(self)
            if parent is not None:
                self.catalog_name = parent.id

    @property
    def solr_uri(self):
        if self.solr_uri_static:
            return self.solr_uri_static
        elif self.solr_uri_env_var:
            return os.environ[self.solr_uri_env_var]
        elif "solr_uri" in self.__dict__:
            # b/w compat
            return self.__dict__["solr_uri"]
        else:
            raise ValueError("No Solr URI provided")

    @property
    def connection_manager(self):
        if disable_solr:
            raise AssertionError("Solr indexing is temporarily disabled")

        jar = self._p_jar
        oid = self._p_oid

        if jar is None or oid is None:
            # Not yet stored in ZODB, so use _v_temp_cm
            manager = self._v_temp_cm
            if manager is None or manager.solr_uri != self.solr_uri:
                self._v_temp_cm = manager = ISolrConnectionManager(self)

        else:
            fc = getattr(jar, "foreign_connections", None)
            if fc is None:
                jar.foreign_connections = fc = {}

            manager = fc.get(oid)
            if manager is None or manager.solr_uri != self.solr_uri:
                manager = ISolrConnectionManager(self)
                fc[oid] = manager

        return manager

    def getIndexSourceNames(self):
        """Get a sequence of attribute names that are indexed by the index."""
        if disable_solr:
            return []

        cm = self.connection_manager
        names = [field.name for field in cm.schema.fields]
        return names

    def getIndexQueryNames(self):
        """Get a sequence of query parameter names to which this index applies."""
        if disable_solr:
            return []
        return (self.id,)

    def getEntryForObject(self, documentId, default=None):
        """Return the information stored for documentId"""
        if disable_solr:
            return None

        cm = self.connection_manager
        uniqueKey = cm.schema.uniqueKey
        response = cm.connection.query(
            q='%s:"%d"' % (uniqueKey, documentId), fields="*"
        )
        results = list(response)
        if results:
            return results[0]
        else:
            return None

    def index_object(self, documentId, obj, threshold=None):
        """Index an object.

        'documentId' is the integer ID of the document.
        'obj' is the object to be indexed.
        'threshold' is the number of words to process between committing
        subtransactions.  If None, subtransactions are disabled.
        """
        if disable_solr:
            return 0

        cm = self.connection_manager
        values = {}
        uniqueKey = cm.schema.uniqueKey
        values[uniqueKey] = documentId
        obj = queryAdapter(obj, ISolrIndexingWrapper, default=obj)

        for field in cm.schema.fields:
            name = field.name
            if name == uniqueKey:
                continue
            value = getattr(obj, name, None)
            if callable(value):
                value = value()
            # Decode all strings using list from `expected_encodings`
            if isinstance(value, str):
                value = self._decode_param(value)
            elif isinstance(value, RichTextValue):
                value = value.output
            value_list = field.handler.convert(value)
            if value_list:
                values[name] = value_list

        cm.set_changed()
        log.debug("indexing %d", documentId)
        cm.connection.add(**values)
        return 1

    def unindex_object(self, documentId):
        """Remove the documentId from the index."""
        if disable_solr:
            return

        cm = self.connection_manager
        cm.set_changed()
        log.debug("unindexing %d", documentId)
        cm.connection.delete(documentId)

    def _apply_index(self, request, cid=""):
        """Apply query specified by request, a mapping containing the query.

        Returns two objects on success: the resultSet containing the
        matching record numbers, and a tuple containing the names of
        the fields used.

        Returns None if request is not valid for this index.
        """
        if disable_solr:
            return None

        cm = self.connection_manager
        queried = []  # List of field names queried
        stored = []  # List of stored field names
        solr_params = {}

        # Get the Solr parameters from the catalog query
        if "solr_params" in request:
            solr_params.update(request["solr_params"])

        # Include parameters from field queries
        for field in cm.schema.fields:
            name = field.name
            if field.stored:
                stored.append(name)
            if name not in request:
                continue

            field_query = self._decode_param(request[name])
            field_params = field.handler.parse_query(field, field_query)
            if field_params:
                queried.append(name)
                for k, to_add in field_params.items():
                    if k not in solr_params:
                        solr_params[k] = to_add
                    else:
                        # add to the list
                        v = solr_params[k]
                        if not isinstance(v, list):
                            v = [v]
                            solr_params[k] = v
                        if isinstance(to_add, str):
                            v.append(to_add)
                        else:
                            v.extend(to_add)

        if not solr_params:
            return None

        solr_params["fields"] = cm.schema.uniqueKey
        # We only add highlighting for any field that is marked as stored.
        # 'queried' returns the list of fields queried,
        # a specific list of names will narrow the list.
        to_highlight = []
        hfields = solr_params.get("highlight", None)
        if hfields and stored:
            if hfields == "queried":
                solr_params["highlight"] = queried
            for fname in hfields:
                if fname in stored:
                    to_highlight.append(fname)
                else:
                    log.debug(
                        "Requested field isn't marked as 'stored', "
                        "cannot enable highlighting: %s",
                        fname,
                    )
            solr_params["highlight"] = to_highlight
        if not solr_params.get("q"):
            # Solr requires a 'q' parameter, so provide an
            # all-inclusive one. If the query is using dismax, then
            # use the 'q.alt' parameter since dismax does not know how
            # to parse '*:*' in the 'q' param.
            if solr_params.get("defType", "") == "dismax":
                solr_params["q.alt"] = "*:*"
                solr_params["q"] = ""
            else:
                solr_params["q"] = "*:*"

        # Additional fields can be added into the query above in the
        # field_params check. The 'q' variable cannot be sent to solr
        # multiple times (as is the case when it is a list). Only the
        # first instance of the 'q' param will be recognized by solr, so
        # we turn it back into a string here.
        #
        # XXX: Should the logic for field_params be changed above?
        if isinstance(solr_params["q"], list):
            solr_params["q"] = " ".join(solr_params["q"])

        # Decode all strings using list from `expected_encodings`
        transcoded_params = self._transcode_params(solr_params)

        log.debug("querying: %r", solr_params)
        response = cm.connection.query(**transcoded_params)
        if "solr_callback" in request:
            # Call a function with the Solr response object
            callback = request["solr_callback"]
            callback(response)

        # Since highlighting can be either enabled by default in the Solr
        # config, or as a query parameter we just check to see if the
        # response has any highlighting returned.
        if hasattr(response, "highlighting"):
            catalog = get_catalog(self, name=self.catalog_name)
            if catalog:
                hkey = tuple(sorted([(fname, request.get(fname)) for fname in queried]))
                if (
                    not issubclass(catalog._v_brains, HighlightingBrain)
                    or (
                        hasattr(catalog._v_brains, "highlighting_key")
                        and catalog._v_brains.highlighting_key != hkey
                    )
                    or (
                        hasattr(catalog._v_brains, "catalog_name")
                        and catalog._v_brains.catalog_name != self.catalog_name
                    )
                ):
                    # We use an inline class here so that the brain has
                    # enough data to retrieve the stored highlighting data
                    class myhighlightingbrains(HighlightingBrain):
                        highlighting_key = hkey
                        highlighting = response.highlighting

                    catalog.useBrains(myhighlightingbrains)
                    log.debug("Creating new custom brain class, hkey: '%s'", hkey)
                else:
                    catalog._v_brains.highlighting = response.highlighting
                    log.debug("Using existing custom brain class, hkey: '%s'", hkey)
            else:
                log.debug(
                    "Cannot retrieve catalog '%s', highlighting unavailable",
                    self.catalog_name,
                )

        uniqueKey = cm.schema.uniqueKey
        result = IIBTree()
        for r in response:
            result[int(r[uniqueKey])] = int(r.get("score", 0) * 1000)

        return result, queried

    def _transcode_params(self, params):
        transcoded_params = {}
        for key, val in params.items():
            enc_val = None
            if isinstance(val, bytes):
                enc_val = self._decode_param(val)
            elif isinstance(val, list):
                enc_val = []
                for v in val:
                    if isinstance(v, bytes):
                        enc_val.append(self._decode_param(v))
                    else:
                        enc_val.append(v)
            else:
                enc_val = val
            transcoded_params[key] = enc_val
        return transcoded_params

    def _decode_param(self, val):
        if isinstance(val, str):
            return val
        elif isinstance(val, dict):
            return {k: self._decode_param(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [self._decode_param(v) for v in val]
        elif isinstance(val, bytes):
            decoded_val = None
            for encoding in self.expected_encodings:
                try:
                    decoded_val = str(val, encoding)
                except UnicodeDecodeError:
                    continue
            if decoded_val is None:
                # Our escape hatch; if none of the expected encodings
                # work, we fall back to UTF8 and replace characters
                decoded_val = str(val, encoding="utf-8", errors="replace")
            return decoded_val
        else:
            return val

    # The ZCatalog Index management screen uses these methods

    def numObjects(self):
        """Return number of unique words in the index"""
        return 0

    def indexSize(self):
        """Return the number of indexed objects"""
        if disable_solr:
            return 0

        cm = self.connection_manager
        response = cm.connection.query(q="*:*", rows="0")
        return int(response.numFound)

    def clear(self):
        """Empty the index"""
        if disable_solr:
            return

        cm = self.connection_manager
        cm.set_changed()
        cm.connection.delete_query("*:*")


class NoRollbackSavepoint:
    def __init__(self, datamanager):
        self.datamanager = datamanager

    def rollback(self):
        pass


@implementer(ISolrConnectionManager, IDataManager)
class SolrConnectionManager:
    def __init__(self, solr_index, connection_factory=SolrConnection):
        self.solr_uri = solr_index.solr_uri
        self._joined = False
        self._connection_factory = connection_factory
        self._connection = connection_factory(self.solr_uri)
        self.schema = SolrSchema(self.solr_uri)

    @property
    def connection(self):
        c = self._connection
        if c is None:
            c = self._connection_factory(self.solr_uri)
            self._connection = c
        return c

    def set_changed(self):
        if not self._joined:
            transaction.get().join(self)
            self._joined = True

    def abort(self, transaction):
        try:
            c = self._connection
            if c is not None:
                self._connection = None
                c.close()
        finally:
            self._joined = False

    def tpc_begin(self, transaction):
        pass

    def commit(self, transaction):
        pass

    def tpc_vote(self, transaction):
        # ensure connection is open
        self.connection

    def tpc_finish(self, transaction):
        try:
            try:
                self.connection.commit()
            except Exception:
                self.abort(transaction)
                raise
        finally:
            self._joined = False

    def tpc_abort(self, transaction):
        pass

    def sortKey(self):
        return self.solr_uri

    def savepoint(self, optimistic=False):
        return NoRollbackSavepoint(self)


class HighlightingBrain(AbstractCatalogBrain):
    highlighting = None  # Data returned by Solr, indexed by RID
    highlighting_key = None  # Submitted search terms, to see if we need to
    # rebuild the custom class

    def getHighlighting(self, fields=None, combine_fields=True):
        """This method retrieves the stored highlighting data for a given
            set of fields.
        `fields` is a sequence of field names to restrict the output to.
        `combine_fields` forces the output to a single list of highlighted
            snippets.
        If `combine_fields` is False, the output is a dictionary with the
            field name as key and a list of the highlighted snippets as the
            value.
        """
        highlighting = {}
        rid = str(self.getRID())
        brain_highlights = self.highlighting.get(rid, {})
        if fields is None:
            fields = list(brain_highlights.keys())

        for fname, fhighlights in brain_highlights.items():
            if fname not in highlighting:
                highlighting[fname] = []
            if isinstance(fhighlights, (tuple, list)):
                highlighting[fname].extend(fhighlights)
            else:
                highlighting[fname].append(fhighlights)

        results = dict(
            [
                (fname, fhighlights)
                for fname, fhighlights in highlighting.items()
                if fname in fields
            ]
        )

        if combine_fields:
            combined = []
            for val in results.values():
                combined.extend(val)
            return combined
        else:
            return results


def get_catalog(obj, name=None):
    if name is None:
        name = "portal_catalog"
    catalog = getToolByName(obj, name, False)
    if not catalog:
        return None

    if hasattr(catalog, "_catalog"):
        catalog = catalog._catalog
    return catalog


def get_solr_indexes(catalog):
    # Use getIndex to ensure the object is wrapped correctly
    return [
        catalog.getIndex(name)
        for name, idx in catalog.indexes.items()
        if ISolrIndex.providedBy(idx)
    ]
