import nose.tools

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories
import ckan.new_authz as new_authz

assert_equals = nose.tools.assert_equals


class TestHasUserPermissionForGroupOrOrg(object):

    def setup(self):
        helpers.reset_db()
        new_authz.clear_auth_functions_cache()

    def teardown(self):
        new_authz.clear_auth_functions_cache()

    def test_group_user_that_created_it_has_admin_permissions(self):
        user = factories.User()
        group = factories.Group(user=user)

        result = new_authz.has_user_permission_for_group_or_org(group['id'],
                                                                user['name'],
                                                                'admin')

        assert_equals(result, True)

    def test_organization_user_that_created_it_has_admin_permissions(self):
        user = factories.User()
        org = factories.Organization(user=user)

        result = new_authz.has_user_permission_for_group_or_org(org['id'],
                                                                user['name'],
                                                                'admin')

        assert_equals(result, True)

    def test_group_users_not_part_of_it_dont_have_read_permissions(self):
        user = factories.User()
        group = factories.Group()

        result = new_authz.has_user_permission_for_group_or_org(group['id'],
                                                                user['name'],
                                                                'read')

        assert_equals(result, False)

    def test_organization_users_not_part_of_it_dont_have_read_permissions(self):
        user = factories.User()
        org = factories.Organization()

        result = new_authz.has_user_permission_for_group_or_org(org['id'],
                                                                user['name'],
                                                                'read')

        assert_equals(result, False)

    @helpers.change_config('ckan.auth.roles_that_cascade_to_sub_groups', 'admin')
    def test_group_users_with_roles_that_cascade_have_permissions_on_all_its_children(self):
        user = factories.User()
        parent_group = factories.Group(user=user)
        group = factories.Group(groups=[parent_group])

        result = new_authz.has_user_permission_for_group_or_org(group['id'],
                                                                user['name'],
                                                                'admin')

        assert_equals(result, True)

    @helpers.change_config('ckan.auth.roles_that_cascade_to_sub_groups', 'admin')
    def test_organization_users_with_roles_that_cascade_have_permissions_on_all_its_children(self):
        user = factories.User()
        parent_org = factories.Organization(user=user)
        org = factories.Organization(groups=[parent_org])

        result = new_authz.has_user_permission_for_group_or_org(org['id'],
                                                                user['name'],
                                                                'admin')

        assert_equals(result, True)

    def test_group_allows_sysadmins_to_do_anything_to_it(self):
        user = factories.Sysadmin()
        group = factories.Group()

        result = new_authz.has_user_permission_for_group_or_org(group['id'],
                                                                user['name'],
                                                                'admin')

        assert_equals(result, True)

    def test_organization_it_allows_sysadmins_to_do_anything_to_it(self):
        user = factories.Sysadmin()
        org = factories.Organization()

        result = new_authz.has_user_permission_for_group_or_org(org['id'],
                                                                user['name'],
                                                                'admin')

        assert_equals(result, True)

    @helpers.change_config('ckan.auth.default_group_only_permissions', 'read')
    def test_group_its_default_permissions_can_be_overriden_by_config_variable(self):
        user = factories.User()
        group = factories.Group()

        result = new_authz.has_user_permission_for_group_or_org(group['id'],
                                                                user['name'],
                                                                'read')

        assert_equals(result, True)

    @helpers.change_config('ckan.auth.default_org_only_permissions', 'read')
    def test_organization_its_default_permissions_can_be_overriden_by_config_variable(self):
        user = factories.User()
        org = factories.Organization()

        result = new_authz.has_user_permission_for_group_or_org(org['id'],
                                                                user['name'],
                                                                'read')

        assert_equals(result, True)

    @helpers.change_config('ckan.auth.default_group_only_permissions', '')
    @helpers.change_config('ckan.auth.default_org_only_permissions', 'read')
    def test_group_default_org_permissions_dont_override_group_permissions(self):
        user = factories.User()
        group = factories.Group()

        result = new_authz.has_user_permission_for_group_or_org(group['id'],
                                                                user['name'],
                                                                'read')

        assert_equals(result, False)

    @helpers.change_config('ckan.auth.default_group_only_permissions', 'read')
    @helpers.change_config('ckan.auth.default_org_only_permissions', '')
    def test_organization_default_group_permissions_dont_override_org_permissions(self):
        user = factories.User()
        org = factories.Organization()

        result = new_authz.has_user_permission_for_group_or_org(org['id'],
                                                                user['name'],
                                                                'read')

        assert_equals(result, False)

    def test_requires_group_or_organization_id(self):
        user = factories.Sysadmin()

        result = new_authz.has_user_permission_for_group_or_org(None,
                                                                user['name'],
                                                                'admin')

        assert_equals(result, False)

    def test_requires_existent_group_or_organization_id(self):
        user = factories.Sysadmin()

        result = new_authz.has_user_permission_for_group_or_org('inexistent',
                                                                user['name'],
                                                                'admin')

        assert_equals(result, False)

    def test_requires_existent_user_name(self):
        group = factories.Group()

        result = new_authz.has_user_permission_for_group_or_org(group['id'],
                                                                'inexistent',
                                                                'admin')

        assert_equals(result, False)
