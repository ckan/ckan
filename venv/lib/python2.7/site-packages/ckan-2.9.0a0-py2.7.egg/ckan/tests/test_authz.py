# encoding: utf-8

import nose

from ckan import authz as auth

from ckan.tests import helpers


assert_equals = nose.tools.assert_equals


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
