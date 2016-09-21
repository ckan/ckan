# encoding: utf-8

import paste.fixture
from ckan.common import config
import urlparse

import ckan.model as model
import ckan.tests.legacy as tests
import ckan.plugins as plugins
import ckan.lib.helpers as h
import ckanext.textview.plugin as plugin
import ckan.lib.create_test_data as create_test_data
import ckan.config.middleware as middleware


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
    resource_view = plugins.toolkit.get_action('resource_view_create')(
        context, resource_view)
    return resource_view, package, resource_id


class TestTextView(tests.WsgiAppCase):
    view_type = 'text_view'

    @classmethod
    def setup_class(cls):
        cls.config_templates = config['ckan.legacy_templates']
        config['ckan.legacy_templates'] = 'false'
        wsgiapp = middleware.make_app(config['global_conf'], **config)
        plugins.load('text_view')
        cls.app = paste.fixture.TestApp(wsgiapp)
        cls.p = plugin.TextView()

        create_test_data.CreateTestData.create()

        cls.resource_view, cls.package, cls.resource_id = \
            _create_test_view(cls.view_type)

    @classmethod
    def teardown_class(cls):
        config['ckan.legacy_templates'] = cls.config_templates
        plugins.unload('text_view')
        model.repo.rebuild_db()

    def test_can_view(self):
        url_same_domain = urlparse.urljoin(
            config.get('ckan.site_url', '//localhost:5000'),
            '/resource.txt')
        url_different_domain = 'http://some.com/resource.txt'

        data_dict = {'resource': {'format': 'jsonp',
                                  'url': url_different_domain}}
        assert self.p.can_view(data_dict)

        data_dict = {'resource': {'format': 'json', 'url': url_same_domain}}
        assert self.p.can_view(data_dict)

        data_dict = {'resource': {'format': 'xml', 'url': url_same_domain}}
        assert self.p.can_view(data_dict)

        data_dict = {'resource': {'format': 'txt', 'url': url_same_domain}}
        assert self.p.can_view(data_dict)

        data_dict = {'resource': {'format': 'foo', 'url': url_same_domain}}
        assert not self.p.can_view(data_dict)

        data_dict = {'resource': {'format': 'json',
                                  'url': url_different_domain}}
        assert not self.p.can_view(data_dict)

    def test_title_description_iframe_shown(self):
        url = h.url_for(controller='package', action='resource_read',
                        id=self.package.name, resource_id=self.resource_id)
        result = self.app.get(url)
        assert self.resource_view['title'] in result
        assert self.resource_view['description'] in result
        assert 'data-module="data-viewer"' in result.body

    def test_js_included(self):
        url = h.url_for(controller='package', action='resource_view',
                        id=self.package.name, resource_id=self.resource_id,
                        view_id=self.resource_view['id'])
        result = self.app.get(url)
        assert (('text_view.js' in result.body) or
                ('text_view.min.js' in result.body))
