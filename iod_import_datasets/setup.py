#!/usr/bin/env python
from setuptools import setup
import sys


install_requires=[
    'ckanapi',
    'click',
    'openpyxl',
    'validators'
]

setup(
    name='iodimport',
    version='0.1',
    description=
        'A command line interface and Python module for '
        'parsing xlsx iod datasets',
    author='Viderum',
    author_email='info@viderum.com',
    url='https://github.com/smallmedia/iod-ckan',
    packages=[
        'iodimport',
        ],
    install_requires=install_requires,
    zip_safe=False,
    entry_points = """
        [console_scripts]
        iodimport=iodimport.cli:cli
        """
    )