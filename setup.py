# encoding: utf-8

import os
import os.path

# Avoid problem releasing to pypi from vagrant
if os.environ.get('USER', '') == 'vagrant':
    del os.link

try:
    from setuptools import (setup, find_packages,
                            __version__ as setuptools_version)
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import (setup, find_packages,
                            __version__ as setuptools_version)

from ckan import (__version__, __description__, __long_description__,
                  __license__)


#
# Check setuptools version
#

def parse_version(s):
    return map(int, s.split('.'))

HERE = os.path.dirname(__file__)
with open(os.path.join(HERE, 'requirement-setuptools.txt')) as f:
        setuptools_requirement = f.read().strip()
min_setuptools_version = parse_version(setuptools_requirement.split('==')[1])
if parse_version(setuptools_version) < min_setuptools_version:
    raise AssertionError(
        'setuptools version error\n'
        'You need a newer version of setuptools.\n'
        'Install the recommended version:\n'
        '    pip install -r requirement-setuptools.txt\n'
        'and then try again to install ckan into your python environment.'
    )


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
        'datastore = ckanext.datastore.commands:datastore_group',
        'datapusher = ckanext.datapusher.cli:DatapusherCommand',
        'front-end-build = ckan.lib.cli:FrontEndBuildCommand',
        'views = ckan.lib.cli:ViewsCommand',
        'config-tool = ckan.lib.cli:ConfigToolCommand',
        'jobs = ckan.lib.cli:JobsCommand',
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
        'datatables_view = ckanext.datatablesview.plugin:DataTablesView',
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
        'example_igroupform_organization = ckanext.example_igroupform.plugin:ExampleIGroupFormOrganizationPlugin',
        'example_iauthfunctions_v1 = ckanext.example_iauthfunctions.plugin_v1:ExampleIAuthFunctionsPlugin',
        'example_iauthfunctions_v2 = ckanext.example_iauthfunctions.plugin_v2:ExampleIAuthFunctionsPlugin',
        'example_iauthfunctions_v3 = ckanext.example_iauthfunctions.plugin_v3:ExampleIAuthFunctionsPlugin',
        'example_iauthfunctions_v4 = ckanext.example_iauthfunctions.plugin_v4:ExampleIAuthFunctionsPlugin',
        'example_iauthfunctions_v5_custom_config_setting = ckanext.example_iauthfunctions.plugin_v5_custom_config_setting:ExampleIAuthFunctionsPlugin',
        'example_iauthfunctions_v6_parent_auth_functions = ckanext.example_iauthfunctions.plugin_v6_parent_auth_functions:ExampleIAuthFunctionsPlugin',
        'example_theme_v01_empty_extension = ckanext.example_theme_docs.v01_empty_extension.plugin:ExampleThemePlugin',
        'example_theme_v02_empty_template = ckanext.example_theme_docs.v02_empty_template.plugin:ExampleThemePlugin',
        'example_theme_v03_jinja = ckanext.example_theme_docs.v03_jinja.plugin:ExampleThemePlugin',
        'example_theme_v04_ckan_extends = ckanext.example_theme_docs.v04_ckan_extends.plugin:ExampleThemePlugin',
        'example_theme_v05_block = ckanext.example_theme_docs.v05_block.plugin:ExampleThemePlugin',
        'example_theme_v06_super = ckanext.example_theme_docs.v06_super.plugin:ExampleThemePlugin',
        'example_theme_v07_helper_function = ckanext.example_theme_docs.v07_helper_function.plugin:ExampleThemePlugin',
        'example_theme_v08_custom_helper_function = ckanext.example_theme_docs.v08_custom_helper_function.plugin:ExampleThemePlugin',
        'example_theme_v09_snippet = ckanext.example_theme_docs.v09_snippet.plugin:ExampleThemePlugin',
        'example_theme_v10_custom_snippet = ckanext.example_theme_docs.v10_custom_snippet.plugin:ExampleThemePlugin',
        'example_theme_v11_HTML_and_CSS = ckanext.example_theme_docs.v11_HTML_and_CSS.plugin:ExampleThemePlugin',
        'example_theme_v12_extra_public_dir = ckanext.example_theme_docs.v12_extra_public_dir.plugin:ExampleThemePlugin',
        'example_theme_v13_custom_css = ckanext.example_theme_docs.v13_custom_css.plugin:ExampleThemePlugin',
        'example_theme_v14_more_custom_css = ckanext.example_theme_docs.v14_more_custom_css.plugin:ExampleThemePlugin',
        'example_theme_v15_fanstatic = ckanext.example_theme_docs.v15_fanstatic.plugin:ExampleThemePlugin',
        'example_theme_v16_initialize_a_javascript_module = ckanext.example_theme_docs.v16_initialize_a_javascript_module.plugin:ExampleThemePlugin',
        'example_theme_v17_popover = ckanext.example_theme_docs.v17_popover.plugin:ExampleThemePlugin',
        'example_theme_v18_snippet_api = ckanext.example_theme_docs.v18_snippet_api.plugin:ExampleThemePlugin',
        'example_theme_v19_01_error = ckanext.example_theme_docs.v19_01_error.plugin:ExampleThemePlugin',
        'example_theme_v19_02_error_handling = ckanext.example_theme_docs.v19_02_error_handling.plugin:ExampleThemePlugin',
        'example_theme_v20_pubsub = ckanext.example_theme_docs.v20_pubsub.plugin:ExampleThemePlugin',
        'example_theme_v21_custom_jquery_plugin = ckanext.example_theme_docs.v21_custom_jquery_plugin.plugin:ExampleThemePlugin',
        'example_theme_custom_config_setting = ckanext.example_theme_docs.custom_config_setting.plugin:ExampleThemePlugin',
        'example_theme_custom_emails = ckanext.example_theme_docs.custom_emails.plugin:ExampleCustomEmailsPlugin',
        'example_iresourcecontroller = ckanext.example_iresourcecontroller.plugin:ExampleIResourceControllerPlugin',
        'example_ivalidators = ckanext.example_ivalidators.plugin:ExampleIValidatorsPlugin',
        'example_iconfigurer = ckanext.example_iconfigurer.plugin:ExampleIConfigurerPlugin',
        'example_itranslation = ckanext.example_itranslation.plugin:ExampleITranslationPlugin',
        'example_iconfigurer_v1 = ckanext.example_iconfigurer.plugin_v1:ExampleIConfigurerPlugin',
        'example_iconfigurer_v2 = ckanext.example_iconfigurer.plugin_v2:ExampleIConfigurerPlugin',
        'example_flask_iblueprint = ckanext.example_flask_iblueprint.plugin:ExampleFlaskIBlueprintPlugin',
        'example_iuploader = ckanext.example_iuploader.plugin:ExampleIUploader',
        'example_idatastorebackend = ckanext.example_idatastorebackend.plugin:ExampleIDatastoreBackendPlugin',
        'example_ipermissionlabels = ckanext.example_ipermissionlabels.plugin:ExampleIPermissionLabelsPlugin',
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
        'example_datastore_deleted_with_count_plugin = ckanext.datastore.tests.test_chained_action:ExampleDataStoreDeletedWithCountPlugin',
        'test_datastore_view = ckan.tests.lib.test_datapreview:MockDatastoreBasedResourceView',
        'test_datapusher_plugin = ckanext.datapusher.tests.test_interfaces:FakeDataPusherPlugin',
        'test_routing_plugin = ckan.tests.config.test_middleware:MockRoutingPlugin',
        'test_flash_plugin = ckan.tests.config.test_sessions:FlashMessagePlugin',
        'test_helpers_plugin = ckan.tests.lib.test_helpers:TestHelpersPlugin',
        'test_feed_plugin = ckan.tests.controllers.test_feed:MockFeedPlugin',
        'test_js_translations_plugin = ckan.tests.lib.test_i18n:TestJSTranslationsPlugin',
    ],
    'babel.extractors': [
        'ckan = ckan.lib.extract:extract_ckan',
    ],
}

setup(
    name='ckan',
    version=__version__,
    author='https://github.com/ckan/ckan/graphs/contributors',
    author_email='info@ckan.org',
    license=__license__,
    url='http://ckan.org/',
    description=__description__,
    keywords='data packaging component tool server',
    long_description=__long_description__,
    zip_safe=False,
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['ckanext', 'ckanext.stats'],
    message_extractors={
        'ckan': [
            ('templates/importer/**', 'ignore', None),
            ('templates/**.html', 'ckan', None),
            ('templates/**.txt', 'ckan', None),
            ('templates_legacy/**.html', 'ckan', None),
            ('public/base/test/**', 'ignore', None),
            ('**.py', 'python', None),
            ('**.js', 'javascript', None),
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
    classifiers=[
        # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2 :: Only',
        'Programming Language :: Python :: 2.7',
    ],
    # this is used to fix an incompatiblity with readthedocs dependencies
    extras_require={
        "readthedocs":  ["Jinja2>=2.3"],
    }
)
