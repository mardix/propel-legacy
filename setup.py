"""
propel
"""

from setuptools import setup
import propel

PACKAGE = propel

setup(
    name=PACKAGE.__NAME__,
    version=PACKAGE.__version__,
    license=PACKAGE.__license__,
    author=PACKAGE.__author__,
    author_email='mardix@github.com',
    description="A package to deploy sites in virtualenv, run scripts, and deploy workers with supervisor",
    long_description=PACKAGE.__doc__,
    url='http://github.com/mardix/propel/',
    download_url='http://github.com/mardix/propel/tarball/master',
    py_modules=['propel'],
    entry_points=dict(console_scripts=['propel=propel:cmd',
                                       'propel-setup=propel:setup_propel']),
    install_requires=[
        'jinja2==2.7.3',
        'pyyaml==3.11',
        'virtualenvwrapper==4.5.1',
        'supervisor'
    ],
    keywords=['deploy', 'flask', 'gunicorn', 'django', 'workers', 'deploy sites', 'deployapp'],
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
