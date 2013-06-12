try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

from ckan import __version__, __description__, __long_description__, __license__

install_requires = [
    'Babel>=0.9.6',
    'Genshi==0.6',
    'Jinja2>=2.6',
    'Pylons==0.9.7',
    'WebTest==1.4.3',  # need to pin this so that Pylons does not install a newer version that conflicts with WebOb==1.0.8
    'apachemiddleware>=0.1.1',
    'babel>=0.9.6',
    'fanstatic==0.12',
    'formalchemy>=1.4.2',
    'markupsafe>=0.15',
    'ofs>=0.4.1',
    'pairtree>=0.7.1-T',
    'paste>=1.7.5.1',
    'psycopg2==2.4.5',
    'python-dateutil>=1.5.0,<2.0.0',
    'pyutilib.component.core>=4.5.3',
    'repoze.who-friendlyform>=1.0.8',
    'repoze.who.plugins.openid>=0.5.3',
    'repoze.who==1.0.19',
    'requests==1.1.0',
    'routes>=1.13',
    'solrpy>=0.9.5',
    'sqlalchemy-migrate>=0.7.2',
    'sqlalchemy==0.7.8',
    'tempita>=0.5.1',
    'vdm>=0.11',
    'webhelpers>=1.3',
    'webob==1.0.8',
    'zope.interface>=4.0.1',
    'unicodecsv>=0.9',
]

dev_requires = [
    'ckanclient>=0.10',
    'docutils>=0.8.1',
    'httpretty>=0.5',
    'nose>=1.2.1',
    'pip-tools>=0.3.1',
    'Sphinx>=1.2b1',
]

dependency_links = [
    'https://github.com/okfn/ckanclient/tarball/master#egg=ckanclient'
]

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
    install_requires=install_requires,
    extras_require={'dev': dev_requires},
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
    message_extractors = {
        'ckan': [
            ('**.py', 'python', None),
            ('**.js', 'javascript', None),
            ('templates/importer/**', 'ignore', None),
            ('templates/**.html', 'ckan', None),
            ('templates_legacy/**.html', 'ckan', None),
            ('ckan/templates/home/language.js', 'genshi', {
                'template_class': 'genshi.template:TextTemplate'
            }),
            ('templates/**.txt', 'genshi', {
                'template_class': 'genshi.template:TextTemplate'
            }),
            ('templates_legacy/**.txt', 'genshi', {
                'template_class': 'genshi.template:TextTemplate'
            }),
            ('public/**', 'ignore', None),
        ],
        'ckanext': [
            ('**.py', 'python', None),
            ('**.html', 'ckan', None),
            ('multilingual/solr/*.txt', 'ignore', None),
            ('**.txt', 'genshi', {
                'template_class': 'genshi.template:TextTemplate'
            }),
        ]
    },
    entry_points="""
    [nose.plugins.0.10]
    main = ckan.ckan_nose_plugin:CkanNose

    [paste.app_factory]
    main = ckan.config.middleware:make_app

    [paste.app_install]
    main = ckan.config.install:CKANInstaller

    [paste.paster_command]
    db = ckan.lib.cli:ManageDb
    create-test-data = ckan.lib.cli:CreateTestDataCommand
    sysadmin = ckan.lib.cli:Sysadmin
    user = ckan.lib.cli:UserCmd
    dataset = ckan.lib.cli:DatasetCmd
    search-index = ckan.lib.cli:SearchIndexCommand
    ratings = ckan.lib.cli:Ratings
    notify = ckan.lib.cli:Notification
    celeryd = ckan.lib.cli:Celery
    rdf-export = ckan.lib.cli:RDFExport
    tracking = ckan.lib.cli:Tracking
    plugin-info = ckan.lib.cli:PluginInfo
    profile = ckan.lib.cli:Profile
    color = ckan.lib.cli:CreateColorSchemeCommand
    check-po-files = ckan.i18n.check_po_files:CheckPoFiles
    trans = ckan.lib.cli:TranslationsCommand
    minify = ckan.lib.cli:MinifyCommand
    less = ckan.lib.cli:LessCommand
    datastore = ckanext.datastore.commands:SetupDatastoreCommand
    front-end-build = ckan.lib.cli:FrontEndBuildCommand


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
    resource_proxy=ckanext.resourceproxy.plugin:ResourceProxy
    text_preview=ckanext.textpreview.plugin:TextPreview
    pdf_preview=ckanext.pdfpreview.plugin:PdfPreview
    recline_preview=ckanext.reclinepreview.plugin:ReclinePreview
    example_itemplatehelpers=ckanext.example_itemplatehelpers.plugin:ExampleITemplateHelpersPlugin
    example_idatasetform=ckanext.example_idatasetform.plugin:ExampleIDatasetFormPlugin

    [ckan.system_plugins]
    domain_object_mods = ckan.model.modification:DomainObjectModificationExtension

    [babel.extractors]
    ckan = ckan.lib.extract:extract_ckan
    """,
    # setup.py test command needs a TestSuite so does not work with py.test
    # test_suite = 'nose.collector',
    # tests_require=[ 'py >= 0.8.0-alpha2' ]
)
