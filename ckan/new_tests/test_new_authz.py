import nose.tools

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories
import ckan.new_authz as new_authz

assert_equals = nose.tools.assert_equals


class TestHasUserPermissionForGroupOrOrg(object):

    def setup(self):
        helpers.reset_db()

    def test_user_that_created_group_has_admin_permissions(self):
        user = factories.User()
        group = factories.Group(user=user)

        result = new_authz.has_user_permission_for_group_or_org(group['id'],
                                                                user['name'],
                                                                'admin')

        assert_equals(result, True)

    def test_users_not_part_of_the_group_dont_have_read_permissions(self):
        user = factories.User()
        group = factories.Group()

        result = new_authz.has_user_permission_for_group_or_org(group['id'],
                                                                user['name'],
                                                                'read')

        assert_equals(result, False)

    def test_users_with_configured_roles_have_permissions_on_all_children_groups(self):
        config_name = 'roles_that_cascade_to_sub_groups'
        original_roles = new_authz.check_config_permission(config_name)
        new_authz.CONFIG_PERMISSIONS[config_name] = ['admin']

        user = factories.User()
        parent_group = factories.Group(user=user)
        group = factories.Group(groups=[parent_group])

        result = new_authz.has_user_permission_for_group_or_org(group['id'],
                                                                user['name'],
                                                                'admin')

        assert_equals(result, True)

        new_authz.CONFIG_PERMISSIONS[config_name] = original_roles

    def test_it_allows_sysadmins_to_do_anything(self):
        user = factories.Sysadmin()
        group = factories.Group()

        result = new_authz.has_user_permission_for_group_or_org(group['id'],
                                                                user['name'],
                                                                'admin')

        assert_equals(result, True)

    def test_it_requires_group_id(self):
        user = factories.Sysadmin()

        result = new_authz.has_user_permission_for_group_or_org(None,
                                                                user['name'],
                                                                'admin')

        assert_equals(result, False)

    def test_it_requires_valid_group_id(self):
        user = factories.Sysadmin()

        result = new_authz.has_user_permission_for_group_or_org('inexistent',
                                                                user['name'],
                                                                'admin')

        assert_equals(result, False)

    def test_it_requires_valid_user_name(self):
        group = factories.Group()

        result = new_authz.has_user_permission_for_group_or_org(group['id'],
                                                                'inexistent',
                                                                'admin')

        assert_equals(result, False)
