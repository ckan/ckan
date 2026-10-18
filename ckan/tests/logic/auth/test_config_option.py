"""Tests for authorization in ckan/logic/auth/config_option.py."""

import pytest

from ckan.tests import factories, helpers

logic = helpers.logic


@pytest.mark.usefixtures("non_clean_db")
def test_config_option_show_anon_user():
    """An anon user is not authorized to use config_option_show action."""
    context = {"user": None, "model": None}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("config_option_show", context=context)


@pytest.mark.usefixtures("non_clean_db")
def test_config_option_show_normal_user():
    """A normal logged in user is not authorized to use config_option_show
    action."""
    fred = factories.User()
    context = {"user": fred["name"], "model": None}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("config_option_show", context=context)


@pytest.mark.usefixtures("non_clean_db")
def test_config_option_show_sysadmin():
    """A sysadmin is authorized to use config_option_show action."""
    fred = factories.Sysadmin()
    context = {"user": fred["name"], "model": None}
    assert helpers.call_auth("config_option_show", context=context)


@pytest.mark.usefixtures("non_clean_db")
def test_config_option_list_anon_user():
    """An anon user is not authorized to use config_option_list action."""
    context = {"user": None, "model": None}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("config_option_list", context=context)


@pytest.mark.usefixtures("non_clean_db")
def test_config_option_list_normal_user():
    """A normal logged in user is not authorized to use config_option_list
    action."""
    fred = factories.User()
    context = {"user": fred["name"], "model": None}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("config_option_list", context=context)


@pytest.mark.usefixtures("non_clean_db")
def test_config_option_list_sysadmin():
    """A sysadmin is authorized to use config_option_list action."""
    fred = factories.Sysadmin()
    context = {"user": fred["name"], "model": None}
    assert helpers.call_auth("config_option_list", context=context)


@pytest.mark.usefixtures("non_clean_db")
def test_config_option_update_anon_user():
    """An anon user is not authorized to use config_option_update
    action."""
    context = {"user": None, "model": None}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("config_option_update", context=context)


@pytest.mark.usefixtures("non_clean_db")
def test_config_option_update_normal_user():
    """A normal logged in user is not authorized to use config_option_update
    action."""
    user = factories.User()
    context = {"user": user["name"], "model": None}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("config_option_update", context=context)


@pytest.mark.usefixtures("non_clean_db")
def test_config_option_update_sysadmin():
    """A sysadmin is authorized to use config_option_update action."""
    user = factories.Sysadmin()
    context = {"user": user["name"], "model": None}
    assert helpers.call_auth("config_option_update", context=context)
