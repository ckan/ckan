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
    ],
    extras_require = {
        'solr': ['solrpy==0.9.4'],
    },
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    package_data={'ckan': [
        'i18n/*/LC_MESSAGES/*.mo',
        'migration/migrate.cfg',
        'migration/README',
        'migration/tests/test_dumps/*',
        'migration/versions/*',
    ]},
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
    [nose.plugins.0.10]
    main = ckan.ckan_nose_plugin:CkanNose

    [paste.app_factory]
    main = ckan.config.middleware:make_app

    [paste.app_install]
    main = pylons.util:PylonsInstaller

    [paste.paster_command]
    db = ckan.lib.cli:ManageDb
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
