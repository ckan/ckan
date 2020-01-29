# encoding: utf-8

import pytest

from ckan import authz as auth

_check = auth.check_config_permission


@pytest.mark.ckan_config("ckan.auth.anon_create_dataset", None)
@pytest.mark.parametrize(
    "perm", ["anon_create_dataset", "ckan.auth.anon_create_dataset"]
)
def test_get_default_value_if_not_set_in_config(perm):
    assert (
        _check(perm) == auth.CONFIG_PERMISSIONS_DEFAULTS["anon_create_dataset"]
    )


@pytest.mark.ckan_config("ckan.auth.anon_create_dataset", True)
def test_config_overrides_default():
    assert _check("anon_create_dataset") is True


@pytest.mark.ckan_config("ckan.auth.anon_create_dataset", True)
def test_config_override_also_works_with_prefix():
    assert _check("ckan.auth.anon_create_dataset") is True


@pytest.mark.ckan_config("ckan.auth.unknown_permission", True)
def test_unknown_permission_returns_false():
    assert _check("unknown_permission") is False


def test_unknown_permission_not_in_config_returns_false():
    assert _check("unknown_permission") is False


def test_default_roles_that_cascade_to_sub_groups_is_a_list():
    assert isinstance(_check("roles_that_cascade_to_sub_groups"), list)


@pytest.mark.ckan_config(
    "ckan.auth.roles_that_cascade_to_sub_groups", "admin editor"
)
def test_roles_that_cascade_to_sub_groups_is_a_list():
    assert sorted(_check("roles_that_cascade_to_sub_groups")) == sorted(
        ["admin", "editor"]
    )
