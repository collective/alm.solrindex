import unittest
import doctest

from zope.testing import doctestunit
from zope.component import testing, eventtesting

from Testing import ZopeTestCase as ztc

from alm.solrindex.tests import base


def test_suite():
    return unittest.TestSuite([
        ztc.FunctionalDocFileSuite(
            'zmi.txt',
            test_class=base.FunctionalTestCase,
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS),
        ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
