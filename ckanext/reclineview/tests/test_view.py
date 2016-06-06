import paste.fixture
import pylons.config as config

import ckan.model as model
import ckan.tests.legacy as tests
import ckan.plugins as p
import ckan.lib.helpers as h
import ckanext.reclineview.plugin as plugin
import ckan.lib.create_test_data as create_test_data
import ckan.config.middleware as middleware

from ckan.tests import helpers, factories


class BaseTestReclineViewBase(tests.WsgiAppCase):
    @classmethod
    def setup_class(cls):
        cls.config_templates = config['ckan.legacy_templates']
        config['ckan.legacy_templates'] = 'false'
        wsgiapp = middleware.make_app(config['global_conf'], **config)
        p.load(cls.view_type)

        cls.app = paste.fixture.TestApp(wsgiapp)
        cls.p = cls.view_class()

        create_test_data.CreateTestData.create()

        cls.resource_view, cls.package, cls.resource_id = \
            _create_test_view(cls.view_type)

    @classmethod
    def teardown_class(cls):
        config['ckan.legacy_templates'] = cls.config_templates
        p.unload(cls.view_type)
        model.repo.rebuild_db()

    def test_can_view(self):
        data_dict = {'resource': {'datastore_active': True}}
        assert self.p.can_view(data_dict)

        data_dict = {'resource': {'datastore_active': False}}
        assert not self.p.can_view(data_dict)

    def test_title_description_iframe_shown(self):
        url = h.url_for(controller='package', action='resource_read',
                        id=self.package.name, resource_id=self.resource_id)
        result = self.app.get(url)
        assert self.resource_view['title'] in result
        assert self.resource_view['description'] in result
        assert 'data-module="data-viewer"' in result.body


class TestReclineView(BaseTestReclineViewBase):
    view_type = 'recline_view'
    view_class = plugin.ReclineView

    def test_it_has_no_schema(self):
        schema = self.p.info().get('schema')
        assert schema is None, schema

    def test_can_view_format_no_datastore(self):
        '''
        Test can_view with acceptable formats when datastore_active is False
        (DataProxy in use).
        '''
        formats = ['CSV', 'XLS', 'TSV', 'csv', 'xls', 'tsv']
        for resource_format in formats:
            data_dict = {'resource': {'datastore_active': False,
                                      'format': resource_format}}
            assert self.p.can_view(data_dict)

    def test_can_view_bad_format_no_datastore(self):
        '''
        Test can_view with incorrect formats when datastore_active is False.
        '''
        formats = ['TXT', 'txt', 'doc', 'JSON']
        for resource_format in formats:
            data_dict = {'resource': {'datastore_active': False,
                                      'format': resource_format}}
            assert not self.p.can_view(data_dict)


class TestReclineViewDatastoreOnly(helpers.FunctionalTestBase):

    @classmethod
    def setup_class(cls):
        if not p.plugin_loaded('recline_view'):
            p.load('recline_view')
        if not p.plugin_loaded('datastore'):
            p.load('datastore')
        app_config = config.copy()
        app_config['ckan.legacy_templates'] = 'false'
        app_config['ckan.plugins'] = 'recline_view datastore'
        app_config['ckan.views.default_views'] = 'recline_view'
        wsgiapp = middleware.make_app(config['global_conf'], **app_config)
        cls.app = paste.fixture.TestApp(wsgiapp)

    @classmethod
    def teardown_class(cls):
        if p.plugin_loaded('recline_view'):
            p.unload('recline_view')
        if p.plugin_loaded('datastore'):
            p.unload('datastore')

    def test_create_datastore_only_view(self):
        dataset = factories.Dataset()
        data = {
            'resource': {'package_id': dataset['id']},
            'fields': [{'id': 'a'}, {'id': 'b'}],
            'records': [{'a': 1, 'b': 'xyz'}, {'a': 2, 'b': 'zzz'}]
        }
        result = helpers.call_action('datastore_create', **data)

        resource_id = result['resource_id']

        url = h.url_for(controller='package', action='resource_read',
                        id=dataset['id'], resource_id=resource_id)

        result = self.app.get(url)

        assert 'data-module="data-viewer"' in result.body


class TestReclineGridView(BaseTestReclineViewBase):
    view_type = 'recline_grid_view'
    view_class = plugin.ReclineGridView

    def test_it_has_no_schema(self):
        schema = self.p.info().get('schema')
        assert schema is None, schema


class TestReclineGraphView(BaseTestReclineViewBase):
    view_type = 'recline_graph_view'
    view_class = plugin.ReclineGraphView

    def test_it_has_the_correct_schema_keys(self):
        schema = self.p.info().get('schema')
        expected_keys = ['offset', 'limit', 'graph_type', 'group', 'series']
        _assert_schema_exists_and_has_keys(schema, expected_keys)


class TestReclineMapView(BaseTestReclineViewBase):
    view_type = 'recline_map_view'
    view_class = plugin.ReclineMapView

    def test_it_has_the_correct_schema_keys(self):
        schema = self.p.info().get('schema')
        expected_keys = ['offset', 'limit', 'map_field_type',
                         'latitude_field', 'longitude_field', 'geojson_field',
                         'auto_zoom', 'cluster_markers']
        _assert_schema_exists_and_has_keys(schema, expected_keys)


def _create_test_view(view_type):
    context = {'model': model,
               'session': model.Session,
               'user': model.User.get('testsysadmin').name}

    package = model.Package.get('annakarenina')
    resource_id = package.resources[1].id
    resource_view = {'resource_id': resource_id,
                     'view_type': view_type,
                     'title': u'Test View',
                     'description': u'A nice test view'}
    resource_view = p.toolkit.get_action('resource_view_create')(
        context, resource_view)
    return resource_view, package, resource_id


def _assert_schema_exists_and_has_keys(schema, expected_keys):
    assert schema is not None, schema

    keys = schema.keys()
    keys.sort()
    expected_keys.sort()

    assert keys == expected_keys, '%s != %s' % (keys, expected_keys)
