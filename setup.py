"""
propel
"""

from setuptools import setup
import propel
from __about__ import *

PACKAGE = propel

setup(
    name=__title__,
    version=__version__,
    license=__license__,
    author=__author__,
    author_email=__email__,
    description=__summary__,
    long_description=PACKAGE.__doc__,
    url=__uri__,
    download_url='http://github.com/mardix/propel/tarball/master',
    py_modules=['propel'],
    entry_points=dict(console_scripts=['propel=propel:cmd',
                                       'propel-setup=propel:setup_propel']),
    install_requires=[
        'jinja2==2.7.3',
        'pyyaml==3.11',
        'virtualenvwrapper==4.5.1'
    ],
    keywords=['deploy', 'propel', 'flask', 'gunicorn', 'django', 'workers', 'deploy sites', 'deployapp'],
    platforms='any',
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    zip_safe=False
)
