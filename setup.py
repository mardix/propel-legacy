"""
DeployPy
"""

from setuptools import setup
import deployapp

PACKAGE = deployapp

setup(
    name=PACKAGE.__NAME__,
    version=PACKAGE.__version__,
    license=PACKAGE.__license__,
    author=PACKAGE.__author__,
    author_email='mardix@github.com',
    description=PACKAGE.__doc__,
    long_description=PACKAGE.__doc__,
    url='http://github.com/mardix/deployapp/',
    download_url='http://github.com/mardix/deployapp/tarball/master',
    py_modules=['deployapp'],
    entry_points=dict(console_scripts=['deployapp=deployapp:cmd']),
    install_requires=[
        'pyyaml',
        'gunicorn',
        'supervisor'
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
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    zip_safe=False
)
