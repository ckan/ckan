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
    url='http://ckan.org/',
    description=__description__,
    keywords='data packaging component tool server',
    long_description =__long_description__,
    install_requires=[
        'routes>=1.9,<=1.11.99',
        'vdm>=0.6,<0.8.99',
        'ckanclient>=0.1,<0.5.99',
        'Pylons>=0.9.7.0,<0.9.7.99',
        'Genshi>=0.6',
        'SQLAlchemy>=0.4.8,<=0.4.99',
        'repoze.who>=1.0.0,<1.0.99',
        'repoze.who.plugins.openid>=0.5.3',
        'pyutilib.component.core>=4.1',
        # uuid in python >= 2.5
        # 'uuid>=1.0',
        # for open licenses
        'licenses==0.4,<0.6.99',
        # last version to work with sqlalchemy < 0.5 
        'sqlalchemy-migrate==0.4.5',
        # latest version of Routes (1.10) depends on webob in middleware but
        # does not declare the dependency!
        # (not sure we need this except in tests but ...)
        'WebOb',
        'FormAlchemy>=1.3.4',
        'carrot>=0.10.5',
        'blinker>=1.0',
        'xlrd>=0.7.1',
        'xlwt>=0.7.2',
        ## required for harvesting
        ## TODO: this could be removed if harvesting moved to worker
        'lxml',
    ],
    extras_require = {
        'solr': ['solrpy>=0.9'],
    },
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    package_data={'ckan': ['i18n/*/LC_MESSAGES/*.mo']},
    message_extractors = {'ckan': [
            ('**.py', 'python', None),
            ('templates/importer/**', 'ignore', None),
            ('templates/**.html', 'genshi', None),
            ('templates/**.js', 'genshi', {
                'template_class': 'genshi.template:TextTemplate'
            }),
            ('templates/**.txt', 'genshi', {
                'template_class': 'genshi.template:TextTemplate'
            }),
            ('public/**', 'ignore', None),
            ]},
    entry_points="""
    [paste.app_factory]
    main = ckan.config.middleware:make_app

    [paste.app_install]
    main = pylons.util:PylonsInstaller

    [paste.paster_command]
    db = ckan.lib.cli:ManageDb
    load = ckan.lib.cli:Load
    create-test-data = ckan.lib.create_test_data:CreateTestData
    sysadmin = ckan.lib.cli:Sysadmin
    search-index = ckan.lib.cli:SearchIndexCommand
    ratings = ckan.lib.cli:Ratings
    changes = ckan.lib.cli:Changes
    notifications = ckan.lib.cli:Notifications
    harvester = ckan.lib.cli:Harvester
    rights = ckan.lib.authztool:RightsCommand
    roles = ckan.lib.authztool:RolesCommand
    
    [paste.paster_create_template]
    ckanext=ckan.pastertemplates:CkanextTemplate

    [ckan.forms]
    standard = ckan.forms.package:get_standard_fieldset
    package = ckan.forms.package:get_standard_fieldset
    group = ckan.forms.group:get_group_fieldset
    package_group = ckan.forms.group:get_package_group_fieldset
    gov = ckan.forms.package_gov:get_gov_fieldset

    [ckan.search]
    sql = ckan.lib.search.sql:SqlSearchBackend

    [ckan.plugins]
    synchronous_search = ckan.lib.search.worker:SynchronousSearchPlugin

    [ckan.system_plugins]
    domain_object_mods = ckan.model.modification:DomainObjectModificationExtension
    """,
    # setup.py test command needs a TestSuite so does not work with py.test
    # test_suite = 'nose.collector',
    # tests_require=[ 'py >= 0.8.0-alpha2' ]
)
