from setuptools import setup
from setuptools import setup, find_packages

setup(
    # If you are changing from the default layout of your extension, you may
    # have to change the message extractors, you can read more about babel
    # message extraction at
    # http://babel.pocoo.org/docs/messages/#extraction-method-mapping-and-configuration
    name='ckanext-viewcount',
    version='0.0.1',
    description='My CKAN Extension',
    author='Hui',
    license='abc',
    packages=find_packages(),
    install_requires=[
    ],
    entry_points='''
        [ckan.plugins]
        viewcount=ckanext.viewcount.plugin:ViewCountPlugin
    ''',
)
