"""A ZCatalog multi-index that uses Solr
"""
import os
from setuptools import setup, find_packages

VERSION = '0.1dev'

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

long_description = (
    read('README.txt')
    + '\n' +
    'Change history\n'
    '**************\n'
    + '\n' +
    read('CHANGES.txt')
    + '\n' +
    'Detailed Documentation\n'
    '**********************\n'
    + '\n' +
    read('alm', 'solrindex', 'README.txt')
    + '\n'
    )

tests_require=['zope.testing']

setup(name='alm.solrindex',
      version=VERSION,
      description=__doc__,
      long_description=long_description,
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        'Framework :: Zope',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        ],
      keywords='zope zcatalog solr plone',
      author='Shane Hathaway',
      author_email='shane@hathawaymix.org',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['alm'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
        'setuptools',
        'solrpy',
        ],
      tests_require=tests_require,
      extras_require=dict(tests=tests_require),
      test_suite = 'alm.solrindex.tests.test_suite',
      )
