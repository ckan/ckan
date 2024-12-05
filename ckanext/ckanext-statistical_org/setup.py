# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    # If you are changing from the default layout of your extension, you may
    # have to change the message extractors, you can read more about babel
    # message extraction at
    # http://babel.pocoo.org/docs/messages/#extraction-method-mapping-and-configuration
     entry_points='''
        [ckan.plugins]
        statistical_org=ckanext.statistical_org.plugin:StatisticalOrgPlugin
    ''',
)
