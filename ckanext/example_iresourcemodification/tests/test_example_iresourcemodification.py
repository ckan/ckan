'''Tests for the ckanext.example_iauthfunctions extension.

'''
import pylons.config as config
import webtest

import ckan.model as model
import ckan.tests as tests

import ckan.plugins
import ckan.new_tests.factories as factories
from ckanext.example_iresourcemodification import plugin


class TestExampleIResourceModification(object):
    '''Tests for the plugin that uses IResourceModification.

    '''

    def setup(self):
        # Set up the test app
        self.app = ckan.config.middleware.make_app(
            config['global_conf'], **config)
        self.app = webtest.TestApp(self.app)

    def teardown(self):
        # Unload the plugin
        ckan.plugins.unload('example_iresourcemodification')
        model.repo.rebuild_db()

    def test_resource_modification_plugin_create(self):
        user = factories.Sysadmin()
        package = factories.Dataset(user=user)

        # Set up the plugin
        ckan.plugins.load('example_iresourcemodification')
        plugin = ckan.plugins.get_plugin('example_iresourcemodification')

        res = tests.call_action_api(self.app, 'resource_create',
                                    package_id=package['id'],
                                    name='test-resource',
                                    url='http://resource.create/',
                                    apikey=user['apikey'])

        assert plugin.counter['before_create'] == 1, plugin.counter
        assert plugin.counter['after_create'] == 1, plugin.counter
        assert plugin.counter['before_update'] == 0, plugin.counter
        assert plugin.counter['after_update'] == 0, plugin.counter
        assert plugin.counter['before_delete'] == 0, plugin.counter
        assert plugin.counter['after_delete'] == 0, plugin.counter

    def test_resource_modification_plugin_update(self):
        user = factories.Sysadmin()
        resource = factories.Resource(user=user)

        # Set up the plugin here because we don't want the resource creation
        # to affect it (because we will only check for changes to update)
        ckan.plugins.load('example_iresourcemodification')
        plugin = ckan.plugins.get_plugin('example_iresourcemodification')

        res = tests.call_action_api(self.app, 'resource_update',
                                    id=resource['id'],
                                    url='http://resource.updated/',
                                    apikey=user['apikey'])

        assert plugin.counter['before_create'] == 0, plugin.counter
        assert plugin.counter['after_create'] == 0, plugin.counter
        assert plugin.counter['before_update'] == 1, plugin.counter
        assert plugin.counter['after_update'] == 1, plugin.counter
        assert plugin.counter['before_delete'] == 0, plugin.counter
        assert plugin.counter['after_delete'] == 0, plugin.counter

    def test_resource_modification_plugin_delete(self):
        user = factories.Sysadmin()
        resource = factories.Resource(user=user)

        # Set up the plugin here because we don't want the resource creation
        # to affect it (because we will only check for changes to delete)
        ckan.plugins.load('example_iresourcemodification')
        plugin = ckan.plugins.get_plugin('example_iresourcemodification')

        res = tests.call_action_api(self.app, 'resource_delete',
                                    id=resource['id'],
                                    apikey=user['apikey'])

        assert plugin.counter['before_create'] == 0, plugin.counter
        assert plugin.counter['after_create'] == 0, plugin.counter
        assert plugin.counter['before_update'] == 0, plugin.counter
        assert plugin.counter['after_update'] == 0, plugin.counter
        assert plugin.counter['before_delete'] == 1, plugin.counter
        assert plugin.counter['after_delete'] == 1, plugin.counter
