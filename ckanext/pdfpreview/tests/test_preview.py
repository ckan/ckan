import pylons

import paste.fixture
from paste.deploy import appconfig

import ckan.logic as logic
import ckan.model as model
import ckan.tests as tests
import ckan.plugins as plugins
import ckan.lib.helpers as h
import ckanext.pdfpreview.plugin as previewplugin
from ckan.lib.create_test_data import CreateTestData
from ckan.config.middleware import make_app


class TestJsonPreview(tests.WsgiAppCase):

    @classmethod
    def setup_class(cls):
        config = appconfig('config:test.ini', relative_to=tests.conf_dir)
        config.local_conf['ckan.plugins'] = 'pdf_preview'
        wsgiapp = make_app(config.global_conf, **config.local_conf)
        cls.app = paste.fixture.TestApp(wsgiapp)

        cls.p = previewplugin.PdfPreview()

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
        cls.resource['format'] = 'pdf'
        logic.action.update.resource_update(context, cls.resource)

    @classmethod
    def teardown_class(cls):
        plugins.reset()

    def test_can_preview(self):
        data_dict = {
            'resource': {
                'format': 'pdf',
                'on_same_domain': True
            }
        }
        assert self.p.can_preview(data_dict)

        data_dict = {
            'resource': {
                'format': 'x-pdf',
                'on_same_domain': True
            }
        }
        assert self.p.can_preview(data_dict)

        data_dict = {
            'resource': {
                'format': 'pdf',
                'on_same_domain': True
            }
        }
        assert self.p.can_preview(data_dict)

        data_dict = {
            'resource': {
                'format': 'pdf',
                'on_same_domain': False
            }
        }
        assert not self.p.can_preview(data_dict)

    def test_js_included(self):
        res_id = self.resource['id']
        pack_id = self.package.name
        url = '/dataset/{0}/resource/{1}/preview'.format(pack_id, res_id)
        result = self.app.get(url, status='*')

        assert result.status == 200, result.status
        assert 'preview_pdf.js' in result.body, result.body
        assert 'preload_resource' in result.body, result.body
        assert 'data-module="pdfpreview"' in result.body, result.body

    def test_iframe_is_shown(self):
        url = h.url_for(controller='package', action='resource_read', id=self.package.name, resource_id=self.resource['id'])
        result = self.app.get(url)
        assert 'data-module="data-viewer"' in result.body, result.body
        assert '<iframe' in result.body, result.body
