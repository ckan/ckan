import pylons.config as config
import paste.fixture

import ckan.config.middleware as middleware
import ckan.model as model
import ckan.lib.helpers as h
import ckan.lib.create_test_data as create_test_data
import ckan.plugins as p
import ckan.tests_legacy as tests


class TestImageView(tests.WsgiAppCase):

    @classmethod
    def setup_class(cls):
        cls.config_templates = config['ckan.legacy_templates']
        config['ckan.legacy_templates'] = 'false'
        wsgiapp = middleware.make_app(config['global_conf'], **config)
        cls.app = paste.fixture.TestApp(wsgiapp)

        create_test_data.CreateTestData.create()

        context = {'model': model,
                   'session': model.Session,
                   'user': model.User.get('testsysadmin').name}

        cls.package = model.Package.get('annakarenina')
        cls.resource_id = cls.package.resources[1].id
        cls.resource_view = {'resource_id': cls.resource_id,
                             'view_type': u'image',
                             'title': u'Image View',
                             'description': u'A nice view',
                             'image_url': 'test-image-view-url'}
        p.toolkit.get_action('resource_view_create')(
            context, cls.resource_view)

    @classmethod
    def teardown_class(cls):
        config['ckan.legacy_templates'] = cls.config_templates
        model.repo.rebuild_db()

    def test_img_is_shown(self):
        url = h.url_for(controller='package', action='resource_read',
                        id=self.package.name, resource_id=self.resource_id)
        result = self.app.get(url)
        assert self.resource_view['image_url'] in result
