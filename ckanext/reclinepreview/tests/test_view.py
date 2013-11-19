import paste.fixture

import pylons.config as config

import ckan.model as model
import ckan.tests as tests
import ckan.plugins as p
import ckan.lib.helpers as h
import ckanext.reclinepreview.plugin as previewplugin
from ckan.lib.create_test_data import CreateTestData
from ckan.config.middleware import make_app


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
    p.toolkit.get_action('resource_view_create')(
        context, resource_view)
    return resource_view, package, resource_id


class TestReclineGrid(tests.WsgiAppCase):
    view_type = 'recline_grid'

    @classmethod
    def setup_class(cls):
        cls.config_templates = config['ckan.legacy_templates']
        config['ckan.legacy_templates'] = 'false'
        wsgiapp = make_app(config['global_conf'], **config)
        p.load(cls.view_type)

        cls.app = paste.fixture.TestApp(wsgiapp)
        cls.p = previewplugin.ReclineGrid()

        CreateTestData.create()

        cls.resource_view, cls.package, cls.resource_id = \
            _create_test_view(cls.view_type)

    @classmethod
    def teardown_class(cls):
        config['ckan.legacy_templates'] = cls.config_templates
        p.unload(cls.view_type)
        model.repo.rebuild_db()

    def test_can_preview(self):
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


class TestReclineGraph(TestReclineGrid):
    view_type = 'recline_graph'


class TestReclineMap(TestReclineGrid):
    view_type = 'recline_map'
