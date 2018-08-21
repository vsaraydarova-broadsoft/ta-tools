# -*- coding: utf-8 -*-

#  Quickstarted Options:
#
#  sqlalchemy: True
#  auth:       sqlalchemy
#  mako:       False
#
#

# This is just a work-around for a Python2.7 issue causing
# interpreter crash at exit when trying to log an info message.
try:
    import logging
    import multiprocessing
except:
    pass

import sys
py_version = sys.version_info[:2]

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

testpkgs = [
    'WebTest >= 1.2.3',
    'nose',
    'coverage',
    'gearbox'
]

install_requires = [
    "TurboGears2 >= 2.3.12",
    "Beaker >= 1.8.0",
    "Kajiki >= 0.6.3",
    "zope.sqlalchemy >= 0.4",
    "sqlalchemy",
    "alembic",
    "repoze.who",
    "tw2.forms",
    "tgext.admin >= 0.6.1",
    "WebHelpers2",
    "requests == 2.9.1",
    "lxml==4.1.1",
    "sleekxmpp==1.3.1",
    "suds==0.4",
    # check if this are required
    "dnspython == 1.12.0",
    "docutils == 0.12",
    "flake8 == 2.5.4",
    "pyasn1 == 0.1.9",
    "pyasn1-modules == 0.0.8",
    "wrapt == 1.10.6"
]

if py_version != (3, 2):
    # Babel not available on 3.2
    install_requires.append("Babel")

setup(
    name='reqaid',
    version='0.1',
    description='',
    author='',
    author_email='',
    url='',
    packages=find_packages(exclude=['ez_setup']),
    install_requires=install_requires,
    include_package_data=True,
    test_suite='nose.collector',
    tests_require=testpkgs,
    package_data={'reqaid': [
        'i18n/*/LC_MESSAGES/*.mo',
        'templates/*/*',
        'public/*/*'
    ]},
    message_extractors={'reqaid': [
        ('**.py', 'python', None),
        ('templates/**.xhtml', 'kajiki', {'strip_text': False, 'extract_python': True}),
        ('public/**', 'ignore', None)
    ]},
    entry_points={
        'paste.app_factory': [
            'main = reqaid.config.middleware:make_app'
        ],
        'gearbox.plugins': [
            'turbogears-devtools = tg.devtools'
        ]
    },
    zip_safe=False
)
