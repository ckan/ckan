# Avoid problem releasing to pypi from vagrant
import os
if os.environ.get('USER', '') == 'vagrant':
    del os.link

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

from ckan import (__version__, __description__, __long_description__,
                  __license__)

entry_points = {
    'nose.plugins.0.10': [
        'main = ckan.ckan_nose_plugin:CkanNose',
    ],
    'paste.app_factory': [
        'main = ckan.config.middleware:make_app',
    ],
    'paste.app_install': [
        'main = ckan.config.install:CKANInstaller',
    ],
    'paste.paster_command': [
        'db = ckan.lib.cli:ManageDb',
        'create-test-data = ckan.lib.cli:CreateTestDataCommand',
        'sysadmin = ckan.lib.cli:Sysadmin',
        'user = ckan.lib.cli:UserCmd',
        'dataset = ckan.lib.cli:DatasetCmd',
        'search-index = ckan.lib.cli:SearchIndexCommand',
        'ratings = ckan.lib.cli:Ratings',
        'notify = ckan.lib.cli:Notification',
        'celeryd = ckan.lib.cli:Celery',
        'rdf-export = ckan.lib.cli:RDFExport',
        'tracking = ckan.lib.cli:Tracking',
        'plugin-info = ckan.lib.cli:PluginInfo',
        'profile = ckan.lib.cli:Profile',
        'color = ckan.lib.cli:CreateColorSchemeCommand',
        'check-po-files = ckan.i18n.check_po_files:CheckPoFiles',
        'trans = ckan.lib.cli:TranslationsCommand',
        'minify = ckan.lib.cli:MinifyCommand',
        'less = ckan.lib.cli:LessCommand',
        'datastore = ckanext.datastore.commands:SetupDatastoreCommand',
        'datapusher = ckanext.datapusher.cli:DatapusherCommand',
        'front-end-build = ckan.lib.cli:FrontEndBuildCommand',
        'views = ckan.lib.cli:ViewsCommand',
        'config-tool = ckan.lib.cli:ConfigToolCommand',
    ],
    'console_scripts': [
        'ckan-admin = bin.ckan_admin:Command',
    ],
    'paste.paster_create_template': [
        'ckanext = ckan.pastertemplates:CkanextTemplate',
    ],
    'ckan.forms': [
        'standard = ckan.forms.package:get_standard_fieldset',
        'package = ckan.forms.package:get_standard_fieldset',
        'group = ckan.forms.group:get_group_fieldset',
        'package_group = ckan.forms.group:get_package_group_fieldset',
    ],
    'ckan.search': [
        'sql = ckan.lib.search.sql:SqlSearchBackend',
        'solr = ckan.lib.search.solr_backend:SolrSearchBackend',
    ],
    'ckan.plugins': [
        'synchronous_search = ckan.lib.search:SynchronousSearchPlugin',
        'stats = ckanext.stats.plugin:StatsPlugin',
        'publisher_form = ckanext.publisher_form.forms:PublisherForm',
        'publisher_dataset_form = ckanext.publisher_form.forms:PublisherDatasetForm',
        'multilingual_dataset = ckanext.multilingual.plugin:MultilingualDataset',
        'multilingual_group = ckanext.multilingual.plugin:MultilingualGroup',
        'multilingual_tag = ckanext.multilingual.plugin:MultilingualTag',
        'multilingual_resource = ckanext.multilingual.plugin:MultilingualResource',
        'organizations = ckanext.organizations.forms:OrganizationForm',
        'organizations_dataset = ckanext.organizations.forms:OrganizationDatasetForm',
        'datastore = ckanext.datastore.plugin:DatastorePlugin',
        'datapusher=ckanext.datapusher.plugin:DatapusherPlugin',
        'test_tag_vocab_plugin = ckanext.test_tag_vocab_plugin:MockVocabTagsPlugin',
        'resource_proxy = ckanext.resourceproxy.plugin:ResourceProxy',
        'text_view = ckanext.textview.plugin:TextView',
        'recline_view = ckanext.reclineview.plugin:ReclineView',
        'recline_grid_view = ckanext.reclineview.plugin:ReclineGridView',
        'recline_graph_view = ckanext.reclineview.plugin:ReclineGraphView',
        'recline_map_view = ckanext.reclineview.plugin:ReclineMapView',
        'image_view = ckanext.imageview.plugin:ImageView',
        'webpage_view = ckanext.webpageview.plugin:WebPageView',
        # FIXME: Remove deprecated resource previews below. You should use the
        # versions as *_view instead.
        'text_preview = ckanext.textview.plugin:TextView',
        'recline_preview = ckanext.reclineview.plugin:ReclineView',
        'recline_grid = ckanext.reclineview.plugin:ReclineGridView',
        'recline_graph = ckanext.reclineview.plugin:ReclineGraphView',
        'recline_map = ckanext.reclineview.plugin:ReclineMapView',
        # End of deprecated previews
        'example_itemplatehelpers = ckanext.example_itemplatehelpers.plugin:ExampleITemplateHelpersPlugin',
        'example_idatasetform = ckanext.example_idatasetform.plugin:ExampleIDatasetFormPlugin',
        'example_idatasetform_v1 = ckanext.example_idatasetform.plugin_v1:ExampleIDatasetFormPlugin',
        'example_idatasetform_v2 = ckanext.example_idatasetform.plugin_v2:ExampleIDatasetFormPlugin',
        'example_idatasetform_v3 = ckanext.example_idatasetform.plugin_v3:ExampleIDatasetFormPlugin',
        'example_idatasetform_v4 = ckanext.example_idatasetform.plugin_v4:ExampleIDatasetFormPlugin',
        'example_igroupform = ckanext.example_igroupform.plugin:ExampleIGroupFormPlugin',
        'example_igroupform_default_group_type = ckanext.example_igroupform.plugin:ExampleIGroupFormPlugin_DefaultGroupType',
        'example_iauthfunctions_v1 = ckanext.example_iauthfunctions.plugin_v1:ExampleIAuthFunctionsPlugin',
        'example_iauthfunctions_v2 = ckanext.example_iauthfunctions.plugin_v2:ExampleIAuthFunctionsPlugin',
        'example_iauthfunctions_v3 = ckanext.example_iauthfunctions.plugin_v3:ExampleIAuthFunctionsPlugin',
        'example_iauthfunctions_v4 = ckanext.example_iauthfunctions.plugin_v4:ExampleIAuthFunctionsPlugin',
        'example_iauthfunctions_v5_custom_config_setting = ckanext.example_iauthfunctions.plugin_v5_custom_config_setting:ExampleIAuthFunctionsPlugin',
        'example_theme_v01_empty_extension = ckanext.example_theme.v01_empty_extension.plugin:ExampleThemePlugin',
        'example_theme_v02_empty_template = ckanext.example_theme.v02_empty_template.plugin:ExampleThemePlugin',
        'example_theme_v03_jinja = ckanext.example_theme.v03_jinja.plugin:ExampleThemePlugin',
        'example_theme_v04_ckan_extends = ckanext.example_theme.v04_ckan_extends.plugin:ExampleThemePlugin',
        'example_theme_v05_block = ckanext.example_theme.v05_block.plugin:ExampleThemePlugin',
        'example_theme_v06_super = ckanext.example_theme.v06_super.plugin:ExampleThemePlugin',
        'example_theme_v07_helper_function = ckanext.example_theme.v07_helper_function.plugin:ExampleThemePlugin',
        'example_theme_v08_custom_helper_function = ckanext.example_theme.v08_custom_helper_function.plugin:ExampleThemePlugin',
        'example_theme_v09_snippet = ckanext.example_theme.v09_snippet.plugin:ExampleThemePlugin',
        'example_theme_v10_custom_snippet = ckanext.example_theme.v10_custom_snippet.plugin:ExampleThemePlugin',
        'example_theme_v11_HTML_and_CSS = ckanext.example_theme.v11_HTML_and_CSS.plugin:ExampleThemePlugin',
        'example_theme_v12_extra_public_dir = ckanext.example_theme.v12_extra_public_dir.plugin:ExampleThemePlugin',
        'example_theme_v13_custom_css = ckanext.example_theme.v13_custom_css.plugin:ExampleThemePlugin',
        'example_theme_v14_more_custom_css = ckanext.example_theme.v14_more_custom_css.plugin:ExampleThemePlugin',
        'example_theme_v15_fanstatic = ckanext.example_theme.v15_fanstatic.plugin:ExampleThemePlugin',
        'example_theme_v16_initialize_a_javascript_module = ckanext.example_theme.v16_initialize_a_javascript_module.plugin:ExampleThemePlugin',
        'example_theme_v17_popover = ckanext.example_theme.v17_popover.plugin:ExampleThemePlugin',
        'example_theme_v18_snippet_api = ckanext.example_theme.v18_snippet_api.plugin:ExampleThemePlugin',
        'example_theme_v19_01_error = ckanext.example_theme.v19_01_error.plugin:ExampleThemePlugin',
        'example_theme_v19_02_error_handling = ckanext.example_theme.v19_02_error_handling.plugin:ExampleThemePlugin',
        'example_theme_v20_pubsub = ckanext.example_theme.v20_pubsub.plugin:ExampleThemePlugin',
        'example_theme_v21_custom_jquery_plugin = ckanext.example_theme.v21_custom_jquery_plugin.plugin:ExampleThemePlugin',
        'example_theme_custom_config_setting = ckanext.example_theme.custom_config_setting.plugin:ExampleThemePlugin',
        'example_iresourcecontroller = ckanext.example_iresourcecontroller.plugin:ExampleIResourceControllerPlugin',
        'example_ivalidators = ckanext.example_ivalidators.plugin:ExampleIValidatorsPlugin',
        'example_iconfigurer = ckanext.example_iconfigurer.plugin:ExampleIConfigurerPlugin',
        'example_itranslation = ckanext.example_itranslation.plugin:ExampleITranslationPlugin',
        'example_iconfigurer_v1 = ckanext.example_iconfigurer.plugin_v1:ExampleIConfigurerPlugin',
        'example_iconfigurer_v2 = ckanext.example_iconfigurer.plugin_v2:ExampleIConfigurerPlugin',
    ],
    'ckan.system_plugins': [
        'domain_object_mods = ckan.model.modification:DomainObjectModificationExtension',
    ],
    'ckan.test_plugins': [
        'routes_plugin = tests.legacy.ckantestplugins:RoutesPlugin',
        'mapper_plugin = tests.legacy.ckantestplugins:MapperPlugin',
        'session_plugin = tests.legacy.ckantestplugins:SessionPlugin',
        'mapper_plugin2 = tests.legacy.ckantestplugins:MapperPlugin2',
        'authorizer_plugin = tests.legacy.ckantestplugins:AuthorizerPlugin',
        'test_observer_plugin = tests.legacy.ckantestplugins:PluginObserverPlugin',
        'action_plugin = tests.legacy.ckantestplugins:ActionPlugin',
        'auth_plugin = tests.legacy.ckantestplugins:AuthPlugin',
        'test_group_plugin = tests.legacy.ckantestplugins:MockGroupControllerPlugin',
        'test_package_controller_plugin = tests.legacy.ckantestplugins:MockPackageControllerPlugin',
        'test_resource_preview = tests.legacy.ckantestplugins:MockResourcePreviewExtension',
        'test_json_resource_preview = tests.legacy.ckantestplugins:JsonMockResourcePreviewExtension',
        'sample_datastore_plugin = ckanext.datastore.tests.sample_datastore_plugin:SampleDataStorePlugin',
        'test_datastore_view = ckan.tests.lib.test_datapreview:MockDatastoreBasedResourceView',
        'test_datapusher_plugin = ckanext.datapusher.tests.test_interfaces:FakeDataPusherPlugin',
    ],
    'babel.extractors': [
        'ckan = ckan.lib.extract:extract_ckan',
    ],
}

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
    message_extractors={
        'ckan': [
            ('**.py', 'python', None),
            ('**.js', 'javascript', None),
            ('templates/importer/**', 'ignore', None),
            ('templates/**.html', 'ckan', None),
            ('templates_legacy/**.html', 'ckan', None),
            ('public/**', 'ignore', None),
        ],
        'ckanext': [
            ('**.py', 'python', None),
            ('**.js', 'javascript', None),
            ('**.html', 'ckan', None),
            ('multilingual/solr/*.txt', 'ignore', None),
        ]
    },
    entry_points=entry_points,
    # setup.py test command needs a TestSuite so does not work with py.test
    # test_suite = 'nose.collector',
    # tests_require=[ 'py >= 0.8.0-alpha2' ]
)
