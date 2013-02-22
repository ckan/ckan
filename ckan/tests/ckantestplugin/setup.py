# After editing this file run python setup.py egg_info in this directory
from setuptools import setup, find_packages
import sys, os

version = '0.0'

setup(name='ckantestplugin',
      version=version,
      description="",
      long_description="""\
""",
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='',
    author_email='',
    url='',
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
    ],
    entry_points={
        'ckan.plugins': [
            'routes_plugin=ckantestplugin:RoutesPlugin',
            'mapper_plugin=ckantestplugin:MapperPlugin',
            'mapper_plugin2=ckantestplugin:MapperPlugin2',
            'authorizer_plugin=ckantestplugin:AuthorizerPlugin',
            'test_observer_plugin=ckantestplugin:PluginObserverPlugin',
            'action_plugin=ckantestplugin:ActionPlugin',
            'auth_plugin=ckantestplugin:AuthPlugin',
        ]
    }
)
