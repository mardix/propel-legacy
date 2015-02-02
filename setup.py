"""
deploysite
"""

from setuptools import setup
import deploysite

PACKAGE = deploysite

setup(
    name=PACKAGE.__NAME__,
    version=PACKAGE.__version__,
    license=PACKAGE.__license__,
    author=PACKAGE.__author__,
    author_email='mardix@github.com',
    description=PACKAGE.__doc__,
    long_description=PACKAGE.__doc__,
    url='http://github.com/mardix/deploysite/',
    download_url='http://github.com/mardix/deploysite/tarball/master',
    py_modules=['deploysite'],
    entry_points=dict(console_scripts=['deploysite=deploysite:cmd']),
    install_requires=[
        'pyyaml',
        'gunicorn',
        'supervisor',
        'gevent',
        'virtualenvwrapper'
    ],
    keywords=['deploy', 'flask'],
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
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    zip_safe=False
)
