#!/usr/bin/env python

from setuptools import setup, find_packages
setup(
    name="klotio-app",
    version="0.3",
    package_dir = {'': 'api/lib'},
    py_modules = ['klotio', 'klotio.models', 'klotio.service', 'klotio.unittest'],
    install_requires=[
        'PyYAML==5.3.1',
        'requests==2.24.0',
        'redis==3.5.2',
        'flask==1.1.2',
        'flask_restful==0.3.8',
        'PyMySQL==0.10.0',
        'SQLAlchemy==1.3.18',
        'SQLAlchemy-JSONField==0.9.0',
        'flask_jsontools==0.1.7'
    ]
)