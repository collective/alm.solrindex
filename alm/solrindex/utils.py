# The following code lifted from Products.CMFCore for portability
from AccessControl import ModuleSecurityInfo
from Acquisition import aq_get
from Acquisition import aq_parent
from Acquisition.interfaces import IAcquirer
from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError


security = ModuleSecurityInfo( 'alm.solrindex.utils' )
_marker = []  # Create a new marker object.
_tool_interface_registry = {}


security.declarePublic('getToolByName')
def getToolByName(obj, name, default=_marker):

    """ Get the tool, 'toolname', by acquiring it.

    o Application code should use this method, rather than simply
      acquiring the tool by name, to ease forward migration (e.g.,
      to Zope3).
    """
    tool_interface = _tool_interface_registry.get(name)

    if tool_interface is not None:
        try:
            utility = getUtility(tool_interface)
            # Site managers, except for five.localsitemanager, return unwrapped
            # utilities. If the result is something which is acquisition-unaware
            # but unwrapped we wrap it on the context.
            if IAcquirer.providedBy(obj) and \
                    aq_parent(utility) is None and \
                    IAcquirer.providedBy(utility):
                utilty = utility.__of__(obj)
            return utility
        except ComponentLookupError:
            # behave in backwards-compatible way
            # fall through to old implementation
            pass

    try:
        tool = aq_get(obj, name, default, 1)
    except AttributeError:
        if default is _marker:
            raise
        return default
    else:
        if tool is _marker:
            raise AttributeError, name
        return tool
