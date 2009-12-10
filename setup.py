# blah
try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

from ckan import __version__, __description__, __long_description__, __license__

setup(
    name='ckan',
    version=__version__,
    author='Open Knowledge Foundation',
    author_email='info@okfn.org',
    license=__license__,
    url='http://www.okfn.org/ckan/',
    description=__description__,
    keywords='data packaging component tool server',
    long_description =__long_description__,
    install_requires=[
        # probably best to get HEAD from repo - see pip-requirements.txt
        'vdm>=0.5a',
        'ckanclient>=0.1,<0.2.99',
        'Pylons>=0.9.7.0,<0.9.7.99',
        'Genshi>=0.4',
        'SQLAlchemy>=0.4.8,<=0.4.99',
        'repoze.who>=1.0.0,<1.0.99',
        'repoze.who.plugins.openid>=0.5,<0.5.99',
        'uuid>=1.0', # in python 2.5 but not before
        # for open licenses
        'licenses',
        # last version to work with sql < 0.5 
        'sqlalchemy-migrate==0.4.5',
        # latest version of Routes (1.10) depends on webob in middleware but
        # does not declare the dependency!
        # (not sure we need this except in tests but ...)
        'WebOb',
        'FormAlchemy>=1.2.3',
        # Excel libaries are only for importer tool
        # 'xlrd>=0.7.1',
        # 'xlwt>=0.7.2',
    ],
    packages=find_packages(exclude=['ez_setup']),
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

    [paste.paster_command]
    db = ckan.lib.cli:ManageDb
    create-test-data = ckan.lib.cli:CreateTestData
    create-search-test-data = ckan.lib.cli:CreateSearchTestData
    test-data = ckan.lib.cli:TestData
    sysadmin = ckan.lib.cli:Sysadmin
    create-search-index = ckan.lib.cli:CreateSearchIndex
    ratings = ckan.lib.cli:Ratings
    """,
    # setup.py test command needs a TestSuite so does not work with py.test
    # test_suite = 'nose.collector',
    # tests_require=[ 'py >= 0.8.0-alpha2' ]
)
