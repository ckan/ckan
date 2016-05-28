# encoding: utf-8

import ckan.lib.helpers as h
import ckan.logic as l
import ckan.model as model
import ckan.lib.create_test_data as create_test_data
import ckan.tests.legacy.functional.base as base
import ckan.plugins as plugins
import ckan.lib.dictization.model_dictize as model_dictize


class TestPluggablePreviews(base.FunctionalTestCase):
    @classmethod
    def setup_class(cls):
        plugins.load('test_resource_preview', 'test_json_resource_preview')
        cls.plugin = plugins.get_plugin('test_resource_preview')

        create_test_data.CreateTestData.create()

        cls.package = model.Package.get('annakarenina')
        cls.resource = cls.package.resources[0]
        cls.url = h.url_for(controller='package',
            action='resource_read',
            id=cls.package.name,
            resource_id=cls.resource.id)
        cls.preview_url = h.url_for(controller='package',
            action='resource_datapreview',
            id=cls.package.id,
            resource_id=cls.resource.id)

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        plugins.unload('test_resource_preview', 'test_json_resource_preview')

    def test_hook(self):
        testpackage = self.package
        resource_dict = model_dictize.resource_dictize(self.resource, {'model': model})

        context = {
            'model': model,
            'session': model.Session,
            'user': model.User.get('testsysadmin').name
        }

        # no preview for type "plain text"
        preview_url = self.preview_url
        result = self.app.get(preview_url, status=409)
        assert 'No preview' in result.body, result.body

        # no preview for type "ümlaut", should not fail
        resource_dict['format'] = u'ümlaut'
        l.action.update.resource_update(context, resource_dict)

        result = self.app.get(preview_url, status=409)
        assert 'No preview' in result.body, result.body

        resource_dict['format'] = 'mock'
        l.action.update.resource_update(context, resource_dict)

        #there should be a preview for type "json"
        preview_url = self.preview_url
        result = self.app.get(preview_url, status=200)

        assert 'mock-preview' in result.body
        assert 'mock-preview.js' in result.body

        assert self.plugin.calls['can_preview'] == 3, self.plugin.calls
        assert self.plugin.calls['setup_template_variables'] == 1, self.plugin.calls
        assert self.plugin.calls['preview_templates'] == 1, self.plugin.calls

        # test whether the json preview is used
        preview_url = h.url_for(controller='package',
                action='resource_datapreview',
                id=testpackage.id,
                resource_id=testpackage.resources[1].id)
        result = self.app.get(preview_url, status=200)

        assert 'mock-json-preview' in result.body
        assert 'mock-json-preview.js' in result.body

        assert self.plugin.calls['can_preview'] == 4, self.plugin.calls
        assert self.plugin.calls['setup_template_variables'] == 1, self.plugin.calls
        assert self.plugin.calls['preview_templates'] == 1, self.plugin.calls

    def test_iframe_is_shown(self):
        result = self.app.get(self.url)
        assert 'data-module="data-viewer"' in result.body, result.body
        assert '<iframe' in result.body, result.body

    def test_iframe_url_is_correct(self):
        result = self.app.get(self.url)
        assert self.preview_url in result.body, (self.preview_url, result.body)
