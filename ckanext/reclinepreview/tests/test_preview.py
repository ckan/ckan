import pylons
import paste.fixture

import pylons.config as config

import ckan.logic as logic
import ckan.model as model
import ckan.tests as tests
import ckan.plugins as plugins
import ckan.lib.helpers as h
import ckanext.reclinepreview.plugin as previewplugin
from ckan.lib.create_test_data import CreateTestData
from ckan.config.middleware import make_app


class TestJsonPreview(tests.WsgiAppCase):

    @classmethod
    def setup_class(cls):
        wsgiapp = make_app(config['global_conf'], **config)
        plugins.load('recline_preview')
        cls.app = paste.fixture.TestApp(wsgiapp)

        cls.p = previewplugin.ReclinePreview()

        # create test resource
        CreateTestData.create()

        context = {
            'model': model,
            'session': model.Session,
            'user': model.User.get('testsysadmin').name
        }

        cls.package = model.Package.get('annakarenina')
        cls.resource = logic.get_action('resource_show')(context, {'id': cls.package.resources[1].id})
        cls.resource['url'] = pylons.config.get('ckan.site_url', '//localhost:5000')
        cls.resource['format'] = 'csv'
        logic.action.update.resource_update(context, cls.resource)

    @classmethod
    def teardown_class(cls):
        plugins.unload('recline_preview')
        CreateTestData.delete()

    def test_can_preview(self):
        data_dict = {
            'resource': {
                'format': 'csv'
            }
        }
        assert self.p.can_preview(data_dict)

        data_dict = {
            'resource': {
                'format': 'tsv'
            }
        }
        assert self.p.can_preview(data_dict)

        data_dict = {
            'resource': {
                'format': 'xls'
            }
        }
        assert self.p.can_preview(data_dict)

        data_dict = {
            'resource': {
                'format': 'csv',
                'on_same_domain': True
            }
        }
        assert self.p.can_preview(data_dict)

        data_dict = {
            'resource': {
                'format': 'csv',
                'on_same_domain': False
            }
        }
        assert self.p.can_preview(data_dict)

        data_dict = {
            'resource': {
                'format': 'foo',
            }
        }
        assert not self.p.can_preview(data_dict)

        data_dict = {
            'resource': {
                'format': 'foo',
                'datastore_active': True
            }
        }
        assert self.p.can_preview(data_dict)

        data_dict = {
            'resource': {
                'format': 'foo',
                'datastore_active': False
            }
        }
        assert not self.p.can_preview(data_dict)


    def test_js_included(self):
        res_id = self.resource['id']
        pack_id = self.package.name
        url = '/dataset/{0}/resource/{1}/preview'.format(pack_id, res_id)
        result = self.app.get(url, status='*')

        assert result.status == 200, result.status
        assert (('preview_recline.js' in result.body) or ('preview_recline.min.js' in result.body))
        assert 'preload_resource' in result.body
        assert 'data-module="reclinepreview"' in result.body

    def test_iframe_is_shown(self):
        url = h.url_for(controller='package', action='resource_read', id=self.package.name, resource_id=self.resource['id'])
        result = self.app.get(url)
        assert 'data-module="data-viewer"' in result.body
        assert '<iframe' in result.body
