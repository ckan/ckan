"""Tests for actions and authorization in ckan/logic/action/status.py."""

import pytest

import ckan.logic as logic
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan import __version__


def test_help_show_basic():

    function_name = "package_search"

    result = helpers.call_action("help_show", name=function_name)

    function = logic.get_action(function_name)

    assert result == function.__doc__


def test_help_show_no_docstring():

    function_name = "package_search"

    function = logic.get_action(function_name)

    actual_docstring = function.__doc__

    function.__doc__ = None

    result = helpers.call_action("help_show", name=function_name)

    function.__doc__ = actual_docstring

    assert result is None


def test_help_show_not_found():

    function_name = "unknown_action"

    with pytest.raises(logic.NotFound):
        helpers.call_action("help_show", name=function_name)


@pytest.mark.ckan_config("ckan.plugins", "stats")
@pytest.mark.usefixtures("clean_db", "with_plugins")
def test_status_show():

    status = helpers.call_action("status_show")

    assert status["ckan_version"] == __version__
    assert status["site_url"] == "http://test.ckan.net"
    assert status["site_title"] == "CKAN"
    assert status["site_description"] == ""
    assert status["locale_default"] == "en"

    assert isinstance(status["extensions"], list)
    assert status["extensions"] == ["stats"]


@pytest.mark.ckan_config("ckan.plugins", "stats")
@pytest.mark.ckan_config("ckan.hide_version", True)
@pytest.mark.usefixtures("with_plugins")
def test_status_show_hiding_version():

    status = helpers.call_action("status_show")

    assert "ckan_version" not in status, "Should have skipped CKAN version"
    assert status["site_url"] == "http://test.ckan.net"
    assert status["site_title"] == "CKAN"
    assert status["site_description"] == ""
    assert status["locale_default"] == "en"

    assert isinstance(status["extensions"], list)
    assert status["extensions"] == ["stats"]


@pytest.mark.ckan_config("ckan.plugins", "stats")
@pytest.mark.ckan_config("ckan.hide_version", True)
@pytest.mark.usefixtures("with_plugins")
def test_status_show_version_to_sysadmins():
    sysadmin = factories.Sysadmin()
    status = helpers.call_action("status_show", context={"user": sysadmin["name"]})

    assert status["ckan_version"] == __version__
    assert status["site_url"] == "http://test.ckan.net"
    assert status["site_title"] == "CKAN"
    assert status["site_description"] == ""
    assert status["locale_default"] == "en"

    assert isinstance(status["extensions"], list)
    assert status["extensions"] == ["stats"]
