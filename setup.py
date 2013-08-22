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
    long_description=__long_description__,
    install_requires=[
    ],
    extras_require={
    },
    zip_safe=False,
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['ckanext', 'ckanext.stats'],
    include_package_data=True,
    package_data={'ckan': [
        'i18n/*/LC_MESSAGES/*.mo',
        'migration/migrate.cfg',
        'migration/README',
        'migration/tests/test_dumps/*',
        'migration/versions/*',
    ]},
    # Not currently translating the admin interface or API
    #
    # Also ignoring templates that are overwritten (or not used) in the
    # ckanext-ecportal extension
    message_extractors={
        'ckan': [
            ('authz.py', 'ignore', None),
            ('new_authz.py', 'ignore', None),
            ('controllers/**.py', 'ignore', None),
            ('forms/**.py', 'ignore', None),
            ('lib/**.py', 'ignore', None),
            ('logic/**.py', 'ignore', None),
            ('model/**.py', 'ignore', None),
            ('tests/**.py', 'ignore', None),
            ('templates/_util.html', 'ignore', None),
            ('templates/admin/**.html', 'ignore', None),
            ('templates/activity_streams/**.html', 'ignore', None),
            ('templates/authorization_group/**.html', 'ignore', None),
            ('templates/facets.html', 'ignore', None),
            ('templates/group/**.html', 'ignore', None),
            ('templates/home/index.html', 'ignore', None),
            ('templates/home/about.html', 'ignore', None),
            ('templates/importer/**.html', 'ignore', None),
            ('templates/js_strings.html', 'ignore', None),
            ('templates/layout_base.html', 'ignore', None),
            ('templates/package/authz.html', 'ignore', None),
            ('templates/package/edit.html', 'ignore', None),
            ('templates/package/editresources.html', 'ignore', None),
            ('templates/package/edit_form.html', 'ignore', None),
            ('templates/package/followers.html', 'ignore', None),
            ('templates/package/form.html', 'ignore', None),
            ('templates/package/form_extra_fields.html', 'ignore', None),
            ('templates/package/form_fields.html', 'ignore', None),
            ('templates/package/form_resources.html', 'ignore', None),
            ('templates/package/history.html', 'ignore', None),
            ('templates/package/layout.html', 'ignore', None),
            ('templates/package/new.html', 'ignore', None),
            ('templates/package/new_package_form.html', 'ignore', None),
            ('templates/package/read.html', 'ignore', None),
            ('templates/package/read_core.html', 'ignore', None),
            ('templates/package/related_list.html', 'ignore', None),
            ('templates/package/resource_read.html', 'ignore', None),
            ('templates/package/resources.html', 'ignore', None),
            ('templates/package/search.html', 'ignore', None),
            ('templates/related/**.html', 'ignore', None),
            ('templates/revision/**.html', 'ignore', None),
            ('templates/snippets/**.html', 'ignore', None),
            ('templates/storage/**.html', 'ignore', None),
            ('templates/user/**.html', 'ignore', None),
            ('**.py', 'python', None),
            ('templates/**.html', 'genshi', None),
            ('ckan/templates/home/language.js', 'genshi', {
                'template_class': 'genshi.template:TextTemplate'
            }),
            ('templates/**.txt', 'genshi', {
                'template_class': 'genshi.template:TextTemplate'
            }),
            ('public/**', 'ignore', None),
        ],
        # Note: make sure that the path to ckanext-ecportal is
        # correct when updating the list of strings for translation
        '../ckanext-ecportal': [
            ('ckanext/ecportal/auth.py', 'ignore', None),
            ('ckanext/ecportal/validators.py', 'ignore', None),
            ('ckanext/ecportal/templates/email/**.html', 'ignore', None),
            ('ckanext/ecportal/templates/home/about.html', 'ignore', None),
            ('ckanext/ecportal/templates/group/edit.html', 'ignore', None),
            ('ckanext/ecportal/templates/group/layout.html', 'ignore', None),
            ('ckanext/ecportal/templates/js_strings.html', 'ignore', None),
            ('ckanext/ecportal/templates/package/authz.html', 'ignore', None),
            ('ckanext/ecportal/templates/package/edit.html', 'ignore', None),
            ('ckanext/ecportal/templates/package/layout.html', 'ignore', None),
            ('ckanext/ecportal/templates/package/new.html', 'ignore', None),
            ('ckanext/ecportal/templates/package/new_package_form.html',
             'ignore', None),
            ('ckanext/ecportal/templates/publisher/edit.html', 'ignore', None),
            ('ckanext/ecportal/templates/publisher/form.html', 'ignore', None),
            ('ckanext/ecportal/templates/publisher/new.html', 'ignore', None),
            ('ckanext/ecportal/templates/publisher/history.html',
             'ignore', None),
            ('ckanext/ecportal/templates/publisher/layout.html',
             'ignore', None),
            ('ckanext/ecportal/templates/searchcloud/**.html', 'ignore', None),
            ('ckanext/ecportal/templates/user/**.html', 'ignore', None),
            ('ckanext/ecportal/templates/organization_apply.html',
             'ignore', None),
            ('ckanext/ecportal/templates/organization_apply_form.html',
             'ignore', None),
            ('ckanext/ecportal/templates/organization_layout.html',
             'ignore', None),
            ('ckanext/ecportal/templates/organization_users.html',
             'ignore', None),
            ('ckanext/ecportal/templates/organization_users_form.html',
             'ignore', None),
            ('**.py', 'python', None),
            ('**.html', 'genshi', None),
        ]
        # 'ckanext': [
        #     ('**.py', 'python', None),
        #     ('**.html', 'genshi', None),
        #     ('multilingual/solr/*.txt', 'ignore', None),
        #     ('**.txt', 'genshi', {
        #         'template_class': 'genshi.template:TextTemplate'
        #     }),
        # ]},
    },
    entry_points="""
    [nose.plugins.0.10]
    main = ckan.ckan_nose_plugin:CkanNose

    [paste.app_factory]
    main = ckan.config.middleware:make_app

    [paste.app_install]
    main = pylons.util:PylonsInstaller

    [paste.paster_command]
    db = ckan.lib.cli:ManageDb
    create-test-data = ckan.lib.cli:CreateTestDataCommand
    sysadmin = ckan.lib.cli:Sysadmin
    user = ckan.lib.cli:UserCmd
    dataset = ckan.lib.cli:DatasetCmd
    search-index = ckan.lib.cli:SearchIndexCommand
    ratings = ckan.lib.cli:Ratings
    notify = ckan.lib.cli:Notification
    rights = ckan.lib.authztool:RightsCommand
    roles = ckan.lib.authztool:RolesCommand
    celeryd = ckan.lib.cli:Celery
    rdf-export = ckan.lib.cli:RDFExport
    tracking = ckan.lib.cli:Tracking
    plugin-info = ckan.lib.cli:PluginInfo
    profile = ckan.lib.cli:Profile
    check-po-files = ckan.i18n.check_po_files:CheckPoFiles
    datastore = ckanext.datastore.commands:SetupDatastoreCommand

    [console_scripts]
    ckan-admin = bin.ckan_admin:Command

    [paste.paster_create_template]
    ckanext=ckan.pastertemplates:CkanextTemplate

    [ckan.forms]
    standard = ckan.forms.package:get_standard_fieldset
    package = ckan.forms.package:get_standard_fieldset
    group = ckan.forms.group:get_group_fieldset
    package_group = ckan.forms.group:get_package_group_fieldset

    [ckan.search]
    sql = ckan.lib.search.sql:SqlSearchBackend
    solr = ckan.lib.search.solr_backend:SolrSearchBackend

    [ckan.plugins]
    synchronous_search = ckan.lib.search:SynchronousSearchPlugin
    stats=ckanext.stats.plugin:StatsPlugin
    publisher_form=ckanext.publisher_form.forms:PublisherForm
    publisher_dataset_form=ckanext.publisher_form.forms:PublisherDatasetForm
    multilingual_dataset=ckanext.multilingual.plugin:MultilingualDataset
    multilingual_group=ckanext.multilingual.plugin:MultilingualGroup
    multilingual_tag=ckanext.multilingual.plugin:MultilingualTag
    organizations=ckanext.organizations.forms:OrganizationForm
    organizations_dataset=ckanext.organizations.forms:OrganizationDatasetForm
    datastore=ckanext.datastore.plugin:DatastorePlugin
    test_tag_vocab_plugin=ckanext.test_tag_vocab_plugin:MockVocabTagsPlugin

    [ckan.system_plugins]
    domain_object_mods = ckan.model.modification:DomainObjectModificationExtension
    """,
    # setup.py test command needs a TestSuite so does not work with py.test
    # test_suite = 'nose.collector',
    # tests_require=[ 'py >= 0.8.0-alpha2' ]
)
