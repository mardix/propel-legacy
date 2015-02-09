"""
deployapp
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
    description="A package to deploy sites in virtualenv, run scripts, and deploy workers with supervisor",
    long_description=PACKAGE.__doc__,
    url='http://github.com/mardix/deployapp/',
    download_url='http://github.com/mardix/deployapp/tarball/master',
    py_modules=['deployapp'],
    entry_points=dict(console_scripts=['deployapp=deployapp:cmd',
                                       'deployapp-setup=deployapp:setup_deployapp']),
    install_requires=[
        'jinja2',
        'pyyaml',
        'supervisor',
        'virtualenvwrapper'
    ],
    keywords=['deploy', 'flask', 'gunicorn', 'django', 'workers', 'deploy sites'],
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
