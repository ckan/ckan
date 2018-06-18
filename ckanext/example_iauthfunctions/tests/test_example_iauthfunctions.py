# encoding: utf-8

'''Tests for the ckanext.example_iauthfunctions extension.

'''

from nose.tools import assert_raises
from nose.tools import assert_equal

import ckan.model as model
import ckan.plugins
from ckan.plugins.toolkit import NotAuthorized, ObjectNotFound
import ckan.tests.factories as factories
import ckan.logic as logic

import ckan.tests.helpers as helpers


class TestExampleIAuthFunctionsPluginV6ParentAuthFunctions(object):
    '''Tests for the ckanext.example_iauthfunctions.plugin module.

    Specifically tests that overriding parent auth functions will cause
    child auth functions to use the overridden version.
    '''
    @classmethod
    def setup_class(cls):
        '''Nose runs this method once to setup our test class.'''
        # Test code should use CKAN's plugins.load() function to load plugins
        # to be tested.
        ckan.plugins.load('example_iauthfunctions_v6_parent_auth_functions')

    def teardown(self):
        '''Nose runs this method after each test method in our test class.'''
        # Rebuild CKAN's database after each test method, so that each test
        # method runs with a clean slate.
        model.repo.rebuild_db()

    @classmethod
    def teardown_class(cls):
        '''Nose runs this method once after all the test methods in our class
        have been run.

        '''
        # We have to unload the plugin we loaded, so it doesn't affect any
        # tests that run after ours.
        ckan.plugins.unload('example_iauthfunctions_v6_parent_auth_functions')

    def test_resource_delete_editor(self):
        '''Normally organization admins can delete resources
        Our plugin prevents this by blocking delete organization.

        Ensure the delete button is not displayed (as only resource delete
        is checked for showing this)

        '''
        user = factories.User()
        owner_org = factories.Organization(
            users=[{'name': user['id'], 'capacity': 'admin'}]
        )
        dataset = factories.Dataset(owner_org=owner_org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        with assert_raises(logic.NotAuthorized) as e:
            logic.check_access('resource_delete', {'user': user['name']}, {'id': resource['id']})

        assert_equal(e.exception.message, 'User %s not authorized to delete resource %s' % (user['name'], resource['id']))

    def test_resource_delete_sysadmin(self):
        '''Normally organization admins can delete resources
        Our plugin prevents this by blocking delete organization.

        Ensure the delete button is not displayed (as only resource delete
        is checked for showing this)

        '''
        user = factories.Sysadmin()
        owner_org = factories.Organization(
            users=[{'name': user['id'], 'capacity': 'admin'}]
        )
        dataset = factories.Dataset(owner_org=owner_org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        assert_equal(logic.check_access('resource_delete', {'user': user['name']}, {'id': resource['id']}), True)


class TestExampleIAuthFunctionsCustomConfigSetting(object):
    '''Tests for the plugin_v5_custom_config_setting module.
    '''

    @classmethod
    def setup_class(cls):
        if not ckan.plugins.plugin_loaded('example_iauthfunctions_v5_custom_config_setting'):
            ckan.plugins.load('example_iauthfunctions_v5_custom_config_setting')

    @classmethod
    def teardown_class(cls):
        ckan.plugins.unload('example_iauthfunctions_v5_custom_config_setting')

    def teardown(self):

        # Delete any stuff that's been created in the db, so it doesn't
        # interfere with the next test.
        model.repo.rebuild_db()

    @helpers.change_config('ckan.iauthfunctions.users_can_create_groups', False)
    def test_sysadmin_can_create_group_when_config_is_False(self):
        sysadmin = factories.Sysadmin()
        context = {
            'ignore_auth': False,
            'user': sysadmin['name']
        }
        helpers.call_action('group_create', context, name='test-group')

    @helpers.change_config('ckan.iauthfunctions.users_can_create_groups', False)
    def test_user_cannot_create_group_when_config_is_False(self):
        user = factories.User()
        context = {
            'ignore_auth': False,
            'user': user['name']
        }
        assert_raises(
            NotAuthorized, helpers.call_action, 'group_create',
            context, name='test-group')

    @helpers.change_config('ckan.iauthfunctions.users_can_create_groups', False)
    def test_visitor_cannot_create_group_when_config_is_False(self):
        context = {
            'ignore_auth': False,
            'user': None
        }
        assert_raises(
            NotAuthorized, helpers.call_action, 'group_create',
            context, name='test-group')

    @helpers.change_config('ckan.iauthfunctions.users_can_create_groups', True)
    def test_sysadmin_can_create_group_when_config_is_True(self):
        sysadmin = factories.Sysadmin()
        context = {
            'ignore_auth': False,
            'user': sysadmin['name']
        }
        helpers.call_action('group_create', context, name='test-group')

    @helpers.change_config('ckan.iauthfunctions.users_can_create_groups', True)
    def test_user_can_create_group_when_config_is_True(self):
        user = factories.User()
        context = {
            'ignore_auth': False,
            'user': user['name']
        }
        helpers.call_action('group_create', context, name='test-group')

    @helpers.change_config('ckan.iauthfunctions.users_can_create_groups', True)
    def test_visitor_cannot_create_group_when_config_is_True(self):
        context = {
            'ignore_auth': False,
            'user': None
        }
        assert_raises(
            NotAuthorized, helpers.call_action, 'group_create',
            context, name='test-group')


class BaseTest(object):

    def teardown(self):
        # Rebuild CKAN's database after each test method, so that each test
        # method runs with a clean slate.
        model.repo.rebuild_db()

    def _make_curators_group(self):
        '''This is a helper method for test methods to call when they want
        the 'curators' group to be created.

        '''
        sysadmin = factories.Sysadmin()

        # Create a user who will *not* be a member of the curators group.
        noncurator = factories.User()

        # Create a user who will be a member of the curators group.
        curator = factories.User()

        # Create the curators group, with the 'curator' user as a member.
        users = [{'name': curator['name'], 'capacity': 'member'}]
        context = {
            'ignore_auth': False,
            'user': sysadmin['name']
        }
        curators_group = helpers.call_action(
            'group_create', context, name='curators', users=users)

        return (noncurator, curator, curators_group)


class TestExampleIAuthFunctionsPluginV4(BaseTest):
    '''Tests for the ckanext.example_iauthfunctions.plugin module.

    '''
    @classmethod
    def setup_class(cls):
        '''Nose runs this method once to setup our test class.'''

        # Test code should use CKAN's plugins.load() function to load plugins
        # to be tested.
        if not ckan.plugins.plugin_loaded('example_iauthfunctions_v4'):
            ckan.plugins.load('example_iauthfunctions_v4')

    @classmethod
    def teardown_class(cls):
        '''Nose runs this method once after all the test methods in our class
        have been run.

        '''
        # We have to unload the plugin we loaded, so it doesn't affect any
        # tests that run after ours.
        ckan.plugins.unload('example_iauthfunctions_v4')

    def test_group_create_with_no_curators_group(self):
        '''Test that group_create doesn't crash when there's no curators group.

        '''
        sysadmin = factories.Sysadmin()

        # Make sure there's no curators group.
        assert 'curators' not in helpers.call_action('group_list', {})

        # Make our sysadmin user create a group. CKAN should not crash.
        context = {
            'ignore_auth': False,
            'user': sysadmin['name']
        }
        helpers.call_action('group_create', context, name='test-group')

    def test_group_create_with_visitor(self):
        '''A visitor (not logged in) should not be able to create a group.

        Note: this also tests that the group_create auth function doesn't
        crash when the user isn't logged in.

        '''
        noncurator, curator, curators_group = self._make_curators_group()
        context = {
            'ignore_auth': False,
            'user': None
        }
        assert_raises(
            NotAuthorized, helpers.call_action, 'group_create',
            context, name='this_group_should_not_be_created')

    def test_group_create_with_non_curator(self):
        '''A user who isn't a member of the curators group should not be able
        to create a group.

        '''
        noncurator, curator, curators_group = self._make_curators_group()
        context = {
            'ignore_auth': False,
            'user': noncurator['name']
        }
        assert_raises(
            NotAuthorized, helpers.call_action, 'group_create',
            context, name='this_group_should_not_be_created')

    def test_group_create_with_curator(self):
        '''A member of the curators group should be able to create a group.

        '''
        noncurator, curator, curators_group = self._make_curators_group()
        name = 'my-new-group'
        context = {
            'ignore_auth': False,
            'user': curator['name']
        }
        result = helpers.call_action(
            'group_create', context, name=name)

        assert result['name'] == name


class TestExampleIAuthFunctionsPluginV3(BaseTest):
    '''Tests for the ckanext.example_iauthfunctions.plugin_v3 module.

    '''
    @classmethod
    def setup_class(cls):
        '''Nose runs this method once to setup our test class.'''

        # Test code should use CKAN's plugins.load() function to load plugins
        # to be tested.
        if not ckan.plugins.plugin_loaded('example_iauthfunctions_v3'):
            ckan.plugins.load('example_iauthfunctions_v3')

    @classmethod
    def teardown_class(cls):
        ckan.plugins.unload('example_iauthfunctions_v3')

    def test_group_create_with_no_curators_group(self):
        '''Test that group_create returns a 404 when there's no curators group.

        With this version of the plugin group_create returns a spurious 404
        when a user _is_ logged-in but the site has no curators group.

        '''
        assert 'curators' not in helpers.call_action('group_list', {})

        user = factories.User()

        context = {
            'ignore_auth': False,
            'user': user['name']
        }
        assert_raises(
            ObjectNotFound, helpers.call_action, 'group_create',
            context, name='this_group_should_not_be_created')

    def test_group_create_with_visitor(self):
        '''Test that group_create returns 403 when no one is logged in.

        Since #1210 non-logged in requests are automatically rejected, unless
        the auth function has the appropiate decorator
        '''

        noncurator, curator, curators_group = self._make_curators_group()
        context = {
            'ignore_auth': False,
            'user': None
        }
        assert_raises(
            NotAuthorized, helpers.call_action, 'group_create',
            context, name='this_group_should_not_be_created')


class TestExampleIAuthFunctionsPluginV2(BaseTest):
    '''Tests for the ckanext.example_iauthfunctions.plugin_v2 module.

    '''
    @classmethod
    def setup_class(cls):
        '''Nose runs this method once to setup our test class.'''

        # Test code should use CKAN's plugins.load() function to load plugins
        # to be tested.
        if not ckan.plugins.plugin_loaded('example_iauthfunctions_v2'):
            ckan.plugins.load('example_iauthfunctions_v2')

    @classmethod
    def teardown_class(cls):
        ckan.plugins.unload('example_iauthfunctions_v2')

    def test_group_create_with_curator(self):
        '''Test that a curator can*not* create a group.

        In this version of the plugin, even users who are members of the
        curators group cannot create groups.

        '''
        noncurator, curator, curators_group = self._make_curators_group()
        context = {
            'ignore_auth': False,
            'user': curator['name']
        }
        assert_raises(
            NotAuthorized, helpers.call_action, 'group_create',
            context, name='this_group_should_not_be_created')
