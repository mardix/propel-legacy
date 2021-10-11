"""
Propel

Propel is a package to deploy multiple Python sites/application in virtualenv.

It also allows you to deploy PHP/HTML applications, run scripts and run workers with Supervisor.

For Python application, it uses Virtualenv to isolate each application, Gunicorn+Gevent as the backend server,
Supervisor and Nginx.

For PHP/HTML sites, it just uses the path as it would in normal environment, and you must have php-fpm

Requirements:
    Nginx
    Gunicorn
    Supervisor
    Gevent
    Virtualenvwrapper
    php-fpm

@Author: Mardix
@Copyright: 2015 - 2017 Mardix
@license: MIT

"""

from setuptools import setup, find_packages

from propel.__about__ import *

setup(
    name=__title__,
    version=__version__,
    license=__license__,
    author=__author__,
    author_email=__email__,
    description=__summary__,
    long_description=__doc__,
    url=__uri__,
    download_url='http://github.com/mardix/propel/tarball/master',
    py_modules=['propel'],
    entry_points=dict(console_scripts=['propel=propel:cmd',
                                       'propel-setup=propel:setup_propel']),
    packages=find_packages(),
    install_requires=[
        'jinja2==2.11.3',
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
