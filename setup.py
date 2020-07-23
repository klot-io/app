#!/usr/bin/env python

from setuptools import setup, find_packages
setup(
    name="klotio-app",
    version="0.1",
    package_dir = {'': 'lib'},
    py_modules = ['klotio', 'klotio.mysql', 'klotio.service', 'klotio.unittest'],
    install_requires=[
        'flask==1.0.2',
        'flask_restful==0.3.7',
        'PyYAML==5.1',
        'PyMySQL==0.9.3',
        'redis==2.10.6',
        'SQLAlchemy==1.3.0',
        'SQLAlchemy-JSONField==0.7.1',
        'flask_jsontools==0.1.1-0',
        'requests==2.22',
        'coverage==4.5.1'
    ],
    dependency_links=[
        'opengui @ git+https://github.com/gaf3/opengui.git@v0.5#egg=opengui'
    ]
)