# encoding: utf-8

'''Tests for the ckanext.example_iauthfunctions extension.

'''
from ckan.common import config

import ckan.model as model

import ckan.plugins
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckanext.example_iresourcecontroller import plugin


class TestExampleIResourceController(object):
    '''Tests for the plugin that uses IResourceController.

    '''

    def setup(self):
        # Set up the test app
        self.app = helpers._get_test_app()

    def teardown(self):
        # Unload the plugin
        ckan.plugins.unload('example_iresourcecontroller')
        model.repo.rebuild_db()

    def test_resource_controller_plugin_create(self):
        user = factories.Sysadmin()
        package = factories.Dataset(user=user)

        # Set up the plugin
        ckan.plugins.load('example_iresourcecontroller')
        plugin = ckan.plugins.get_plugin('example_iresourcecontroller')

        res = helpers.call_action('resource_create',
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

    def test_resource_controller_plugin_update(self):
        user = factories.Sysadmin()
        resource = factories.Resource(user=user)

        # Set up the plugin here because we don't want the resource creation
        # to affect it (because we will only check for changes to update)
        ckan.plugins.load('example_iresourcecontroller')
        plugin = ckan.plugins.get_plugin('example_iresourcecontroller')

        res = helpers.call_action('resource_update',
                                  id=resource['id'],
                                  url='http://resource.updated/',
                                  apikey=user['apikey'])

        assert plugin.counter['before_create'] == 0, plugin.counter
        assert plugin.counter['after_create'] == 0, plugin.counter
        assert plugin.counter['before_update'] == 1, plugin.counter
        assert plugin.counter['after_update'] == 1, plugin.counter
        assert plugin.counter['before_delete'] == 0, plugin.counter
        assert plugin.counter['after_delete'] == 0, plugin.counter

    def test_resource_controller_plugin_delete(self):
        user = factories.Sysadmin()
        resource = factories.Resource(user=user)

        # Set up the plugin here because we don't want the resource creation
        # to affect it (because we will only check for changes to delete)
        ckan.plugins.load('example_iresourcecontroller')
        plugin = ckan.plugins.get_plugin('example_iresourcecontroller')

        res = helpers.call_action('resource_delete',
                                  id=resource['id'],
                                  apikey=user['apikey'])

        assert plugin.counter['before_create'] == 0, plugin.counter
        assert plugin.counter['after_create'] == 0, plugin.counter
        assert plugin.counter['before_update'] == 0, plugin.counter
        assert plugin.counter['after_update'] == 0, plugin.counter
        assert plugin.counter['before_delete'] == 1, plugin.counter
        assert plugin.counter['after_delete'] == 1, plugin.counter

    def test_resource_controller_plugin_show(self):
        """
        Before show gets called by the other methods but we test it
        separately here and make sure that it doesn't call the other
        methods.
        """
        user = factories.Sysadmin()
        package = factories.Dataset(user=user)
        resource = factories.Resource(user=user, package_id=package['id'])

        # Set up the plugin here because we don't want the resource creation
        # to affect it (because we will only check for changes to delete)
        ckan.plugins.load('example_iresourcecontroller')
        plugin = ckan.plugins.get_plugin('example_iresourcecontroller')

        res = helpers.call_action('package_show',
                                  name_or_id=package['id'])

        assert plugin.counter['before_create'] == 0, plugin.counter
        assert plugin.counter['after_create'] == 0, plugin.counter
        assert plugin.counter['before_update'] == 0, plugin.counter
        assert plugin.counter['after_update'] == 0, plugin.counter
        assert plugin.counter['before_delete'] == 0, plugin.counter
        assert plugin.counter['after_delete'] == 0, plugin.counter
        assert plugin.counter['before_show'] == 1, plugin.counter
