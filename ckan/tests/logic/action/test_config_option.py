"""Tests for actions and authorization in ckan/logic/action/config_option.py."""

import pytest

from ckan import logic
from ckan.lib import app_globals
from ckan.logic import schema
from ckan.tests import helpers


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.site_title", "My Test CKAN")
def test_config_option_show_in_config_not_in_db():
    """config_option_show returns value from config when value on in
    system_info table."""

    title = helpers.call_action("config_option_show", key="ckan.site_title")
    assert title == "My Test CKAN"


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.site_title", "My Test CKAN")
def test_config_option_show_in_config_and_in_db():
    """config_option_show returns value from db when value is in both
    config and system_info table."""

    params = {"ckan.site_title": "Test site title"}
    helpers.call_action("config_option_update", **params)

    title = helpers.call_action("config_option_show", key="ckan.site_title")
    assert title == "Test site title"


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.not.editable", "My non editable option")
def test_config_option_show_not_whitelisted_key():
    """config_option_show raises exception if key is not a whitelisted
    config option."""

    with pytest.raises(logic.ValidationError):
        helpers.call_action("config_option_show", key="ckan.not.editable")


def test_config_option_list():
    """config_option_list returns whitelisted config option keys"""

    keys = helpers.call_action("config_option_list")
    schema_keys = list(schema.update_configuration_schema().keys())

    assert keys == schema_keys


@pytest.mark.usefixtures("non_clean_db")
def test_app_globals_set_if_defined():
    key = "ckan.site_title"
    value = "Test site title"

    params = {key: value}

    helpers.call_action("config_option_update", **params)

    globals_key = app_globals.get_globals_key(key)
    assert hasattr(app_globals.app_globals, globals_key)

    assert getattr(app_globals.app_globals, globals_key) == value
