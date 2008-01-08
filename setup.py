try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(
    name='ckan',
    version='0.4dev',
    author='Open Knowledge Foundation',
    author_email='info@okfn.org',
    license='MIT',
    url='http://www.okfn.org/ckan/',
    description='Comprehensive Knowledge Archive Network Software',
    long_description =\
'''
CKAN is a web application to manage listings of knowledge packages.
''',
    install_requires=[
        'vdm==0.1',
        'Pylons>=0.9.6.1',
        'SQLObject>=0.7',
        'AuthKit==0.4.0',
        ],
    packages=find_packages(exclude=['ez_setup']),
    scripts = ['bin/ckan-admin'],
    include_package_data=True,
    package_data={'ckan': ['i18n/*/LC_MESSAGES/*.mo']},
    #message_extractors = {'ckan': [
    #        ('**.py', 'python', None),
    #        ('templates/**.mako', 'mako', None),
    #        ('public/**', 'ignore', None)]},
    entry_points="""
    [paste.app_factory]
    main = ckan.config.middleware:make_app

    [paste.app_install]
    main = pylons.util:PylonsInstaller
    """,
    # setup.py test command needs a TestSuite so does not work with pyt.test
    # test_suite = 'nose.collector',
    # tests_require=[ 'py >= 0.8.0-alpha2' ]
)
