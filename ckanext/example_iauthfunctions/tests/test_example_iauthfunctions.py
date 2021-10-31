# encoding: utf-8
'''Tests for the ckanext.example_iauthfunctions extension.

'''
import pytest

import ckan.logic as logic
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan.plugins.toolkit import NotAuthorized, ObjectNotFound


@pytest.mark.ckan_config('ckan.plugins',
                         'example_iauthfunctions_v6_parent_auth_functions')
@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context')
class TestAuthV6(object):
    def test_resource_delete_editor(self):
        '''Normally organization admins can delete resources
        Our plugin prevents this by blocking delete organization.

        Ensure the delete button is not displayed (as only resource delete
        is checked for showing this)

        '''
        user = factories.User()
        owner_org = factories.Organization(users=[{
            'name': user['id'],
            'capacity': 'admin'
        }])
        dataset = factories.Dataset(owner_org=owner_org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        with pytest.raises(logic.NotAuthorized) as e:
            logic.check_access('resource_delete', {'user': user['name']},
                               {'id': resource['id']})

        assert e.value.message == 'User %s not authorized to delete resource %s' % (
            user['name'], resource['id'])

    def test_resource_delete_sysadmin(self):
        '''Normally organization admins can delete resources
        Our plugin prevents this by blocking delete organization.

        Ensure the delete button is not displayed (as only resource delete
        is checked for showing this)

        '''
        user = factories.Sysadmin()
        owner_org = factories.Organization(users=[{
            'name': user['id'],
            'capacity': 'admin'
        }])
        dataset = factories.Dataset(owner_org=owner_org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        assert logic.check_access('resource_delete', {'user': user['name']},
                                  {'id': resource['id']})


@pytest.mark.ckan_config('ckan.plugins',
                         'example_iauthfunctions_v5_custom_config_setting')
@pytest.mark.ckan_config('ckan.iauthfunctions.users_can_create_groups', False)
@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context')
class TestAuthV5(object):

    def test_sysadmin_can_create_group_when_config_is_false(self):
        sysadmin = factories.Sysadmin()
        context = {'ignore_auth': False, 'user': sysadmin['name']}
        helpers.call_action('group_create', context, name='test-group')

    def test_user_cannot_create_group_when_config_is_false(self):
        user = factories.User()
        context = {'ignore_auth': False, 'user': user['name']}
        with pytest.raises(NotAuthorized):
            helpers.call_action('group_create', context, name='test-group')

    def test_visitor_cannot_create_group_when_config_is_false(self):
        context = {'ignore_auth': False, 'user': None}
        with pytest.raises(NotAuthorized):
            helpers.call_action('group_create', context, name='test-group')


@pytest.mark.ckan_config('ckan.plugins',
                         'example_iauthfunctions_v5_custom_config_setting')
@pytest.mark.ckan_config('ckan.iauthfunctions.users_can_create_groups', True)
@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context')
class TestAuthV5WithUserCreateGroup(object):

    def test_sysadmin_can_create_group_when_config_is_true(self):
        sysadmin = factories.Sysadmin()
        context = {'ignore_auth': False, 'user': sysadmin['name']}
        helpers.call_action('group_create', context, name='test-group')

    def test_user_can_create_group_when_config_is_true(self):
        user = factories.User()
        context = {'ignore_auth': False, 'user': user['name']}
        helpers.call_action('group_create', context, name='test-group')

    def test_visitor_cannot_create_group_when_config_is_true(self):
        context = {'ignore_auth': False, 'user': None}
        with pytest.raises(NotAuthorized):
            helpers.call_action('group_create', context, name='test-group')


@pytest.fixture
def curators_group():
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
    context = {'ignore_auth': False, 'user': sysadmin['name']}
    group = helpers.call_action('group_create',
                                context,
                                name='curators',
                                users=users)

    return (noncurator, curator, group)


@pytest.mark.ckan_config('ckan.plugins', 'example_iauthfunctions_v4')
@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context')
def test_group_create_with_no_curators_group():
    '''Test that group_create doesn't crash when there's no curators group.
    '''
    sysadmin = factories.Sysadmin()

    # Make sure there's no curators group.
    assert 'curators' not in helpers.call_action('group_list', {})

    # Make our sysadmin user create a group. CKAN should not crash.
    context = {'ignore_auth': False, 'user': sysadmin['name']}
    helpers.call_action('group_create', context, name='test-group')


@pytest.mark.ckan_config('ckan.plugins', 'example_iauthfunctions_v4')
@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context')
def test_group_create_with_visitor(curators_group):
    '''A visitor (not logged in) should not be able to create a group.

    Note: this also tests that the group_create auth function doesn't
    crash when the user isn't logged in.
    '''
    context = {'ignore_auth': False, 'user': None}
    with pytest.raises(NotAuthorized):
        helpers.call_action('group_create',
                            context,
                            name='this_group_should_not_be_created')


@pytest.mark.ckan_config('ckan.plugins', 'example_iauthfunctions_v4')
@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context')
def test_group_create_with_non_curator(curators_group):
    '''A user who isn't a member of the curators group should not be able
    to create a group.
    '''
    noncurator, _, _ = curators_group
    context = {'ignore_auth': False, 'user': noncurator['name']}
    with pytest.raises(NotAuthorized):
        helpers.call_action('group_create',
                            context,
                            name='this_group_should_not_be_created')


@pytest.mark.ckan_config('ckan.plugins', 'example_iauthfunctions_v4')
@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context')
def test_group_create_with_curator(curators_group):
    '''A member of the curators group should be able to create a group.
    '''
    _, curator, _ = curators_group
    name = 'my-new-group'
    context = {'ignore_auth': False, 'user': curator['name']}
    result = helpers.call_action('group_create', context, name=name)

    assert result['name'] == name


@pytest.mark.ckan_config('ckan.plugins', 'example_iauthfunctions_v3')
@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context')
class TestExampleIAuthFunctionsPluginV3(object):
    def test_group_create_with_no_curators_group_v3(self):
        '''Test that group_create returns a 404 when there's no curators group.

        With this version of the plugin group_create returns a spurious 404
        when a user _is_ logged-in but the site has no curators group.
        '''
        assert 'curators' not in helpers.call_action('group_list', {})

        user = factories.User()

        context = {'ignore_auth': False, 'user': user['name']}
        with pytest.raises(ObjectNotFound):
            helpers.call_action('group_create',
                                context,
                                name='this_group_should_not_be_created')

    def test_group_create_with_visitor_v3(self, curators_group):
        '''Test that group_create returns 403 when no one is logged in.

        Since #1210 non-logged in requests are automatically rejected, unless
        the auth function has the appropiate decorator
        '''

        context = {'ignore_auth': False, 'user': None}
        with pytest.raises(NotAuthorized):
            helpers.call_action('group_create',
                                context,
                                name='this_group_should_not_be_created')


@pytest.mark.ckan_config('ckan.plugins', 'example_iauthfunctions_v2')
@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context')
def test_group_create_with_curator_v2(curators_group):
    '''Test that a curator can*not* create a group.

    In this version of the plugin, even users who are members of the
    curators group cannot create groups.
    '''
    _, curator, _ = curators_group
    context = {'ignore_auth': False, 'user': curator['name']}
    with pytest.raises(NotAuthorized):
        helpers.call_action('group_create',
                            context,
                            name='this_group_should_not_be_created')
