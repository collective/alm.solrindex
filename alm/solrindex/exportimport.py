
from alm.solrindex.interfaces import ISolrIndex
from Products.GenericSetup.interfaces import ISetupEnviron
from Products.GenericSetup.utils import NodeAdapterBase
from Products.GenericSetup.utils import PropertyManagerHelpers
from zope.component import adapts


class SolrIndexNodeAdapter(NodeAdapterBase, PropertyManagerHelpers):

    """GenericSetup node importer and exporter for SolrIndex.
    """

    adapts(ISolrIndex, ISetupEnviron)

    def _exportNode(self):
        """Export the object as a DOM node.
        """
        node = self._getObjectNode('index')
        node.appendChild(self._extractProperties())
        return node

    def _importNode(self, node):
        """Import the object from the DOM node.
        """
        if self.environ.shouldPurge():
            self._purgeProperties()
        self._initProperties(node)

        if node.hasAttribute('clear'):
            # Clear the index
            self.context.clear()

    node = property(_exportNode, _importNode)
