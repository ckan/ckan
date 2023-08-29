# encoding: utf-8

from ckan.lib.app_globals import app_globals as g


def test_config_not_set():
    """ckan.site_about has not been configured. Behaviour has always been
    to return an empty string.

    """
    assert g.site_about == ""


def test_config_set_to_blank():
    """ckan.site_description is configured but with no value. Behaviour
    has always been to return an empty string.

    """
    assert g.site_description == ""
