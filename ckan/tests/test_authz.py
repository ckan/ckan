# encoding: utf-8

import six
import mock
import pytest

from ckan import authz as auth
from ckan.tests import factories

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


@pytest.mark.skipif(six.PY3, reason='Only relevant to py2')
@mock.patch('paste.registry.TypeError')
def test_get_user_outside_web_request_py2(mock_TypeError):
    auth._get_user('example')
    assert mock_TypeError.called


@pytest.mark.skipif(six.PY2, reason='Only relevant to py3')
@mock.patch('flask.globals.RuntimeError')
def test_get_user_outside_web_request_py3(mock_RuntimeError):
    auth._get_user('example')
    assert mock_RuntimeError.called


@pytest.mark.usefixtures('with_request_context', 'clean_db')
def test_get_user_inside_web_request_returns_user_obj():
    user = factories.User()
    assert auth._get_user(user['name']).name == user['name']


@pytest.mark.usefixtures('with_request_context')
def test_get_user_inside_web_request_not_found():

    assert auth._get_user('example') is None
