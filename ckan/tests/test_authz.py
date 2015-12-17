import nose

from ckan import authz as auth

from ckan.tests import helpers


assert_equals = nose.tools.assert_equals
assert_true = nose.tools.assert_true
assert_false = nose.tools.assert_false


class TestCheckConfigPermission(object):

    @helpers.change_config('ckan.auth.anon_create_dataset', None)
    def test_get_default_value_if_not_set_in_config(self):

        assert_equals(auth.check_config_permission(
            'anon_create_dataset'),
            auth.CONFIG_PERMISSIONS_DEFAULTS['anon_create_dataset'])

    @helpers.change_config('ckan.auth.anon_create_dataset', None)
    def test_get_default_value_also_works_with_prefix(self):

        assert_equals(auth.check_config_permission(
            'ckan.auth.anon_create_dataset'),
            auth.CONFIG_PERMISSIONS_DEFAULTS['anon_create_dataset'])

    @helpers.change_config('ckan.auth.anon_create_dataset', True)
    def test_config_overrides_default(self):

        assert_equals(auth.check_config_permission(
            'anon_create_dataset'),
            True)

    @helpers.change_config('ckan.auth.anon_create_dataset', True)
    def test_config_override_also_works_with_prefix(self):

        assert_equals(auth.check_config_permission(
            'ckan.auth.anon_create_dataset'),
            True)

    @helpers.change_config('ckan.auth.unknown_permission', True)
    def test_unknown_permission_returns_false(self):

        assert_equals(auth.check_config_permission(
            'unknown_permission'),
            False)

    def test_unknown_permission_not_in_config_returns_false(self):

        assert_equals(auth.check_config_permission(
            'unknown_permission'),
            False)

    def test_default_roles_that_cascade_to_sub_groups_is_a_list(self):

        assert isinstance(auth.check_config_permission(
            'roles_that_cascade_to_sub_groups'),
            list)

    @helpers.change_config('ckan.auth.roles_that_cascade_to_sub_groups',
                           'admin editor')
    def test_roles_that_cascade_to_sub_groups_is_a_list(self):

        assert_equals(sorted(auth.check_config_permission(
            'roles_that_cascade_to_sub_groups')),
            sorted(['admin', 'editor']))

    def test_auth_is_anon_user_is_false_if_user_is_truthy(self):
        context = {
            'user': 'some-user'
        }
        assert_false(auth.auth_is_anon_user(context))

    def test_auth_is_anon_user_is_true_if_user_wasnt_passed(self):
        context = {}
        assert_true(auth.auth_is_anon_user(context))

    def test_auth_is_anon_user_is_true_if_user_is_falsy(self):
        context = {
            'user': '',
        }
        assert_true(auth.auth_is_anon_user(context))

    def test_auth_is_anon_user_is_true_if_user_is_an_IP(self):
        context = {
            'user': '0.0.0.0',
        }
        assert_true(auth.auth_is_anon_user(context))

    def test_auth_is_anon_user_is_true_if_user_is_Unknown_IP_Address(self):
        context = {
            'user': 'Unknown IP Address',
        }
        assert_true(auth.auth_is_anon_user(context))
