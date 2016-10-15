"""A ZCatalog multi-index that uses Solr

"""
import os
from setuptools import setup, find_packages


def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

long_description = (
    read('README.rst')
    + '\n' +
    'Detailed Documentation\n'
    '======================\n'
    + '\n' +
    read('alm', 'solrindex', 'README.rst')
    + '\n' +
    read('CHANGES.rst')
    + '\n')

here = os.path.abspath(os.path.normpath(os.path.dirname(__file__)))
version_txt = os.path.join(here, 'alm/solrindex/version.txt')
alm_solrindex_version = open(version_txt).read().strip()

setup(
    name='alm.solrindex',
    version=alm_solrindex_version,
    description=__doc__,
    long_description=long_description,
    # Get more strings from
    # http://www.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Framework :: Zope2',
        'Framework :: Plone :: 4.3',
        'Framework :: Plone :: 5.0',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: GNU General Public License (GPL)',
    ],
    keywords='zope zcatalog solr plone',
    author='Six Feet Up, Inc.',
    author_email='info@sixfeetup.com',
    license='BSD',
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['alm'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'setuptools',
        'Products.CMFPlone',
        #'solrpy',  # we have a private copy until solrpy fixes some bugs
    ],
    test_suite='alm.solrindex.tests.test_suite',
    entry_points="""\
    [z3c.autoinclude.plugin]
    target = plone

    [console_scripts]
    waituri = alm.solrindex.scripts.waituri:main
    """,
)
