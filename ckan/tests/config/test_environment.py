# encoding: utf-8

import os

import pytest

from ckan.config import environment
from ckan.exceptions import CkanConfigurationException


@pytest.mark.ckan_config("ckan.site_url", "")
def test_missing_siteurl():
    with pytest.raises(CkanConfigurationException):
        environment.update_config()


@pytest.mark.ckan_config("ckan.site_url", "demo.ckan.org")
def test_siteurl_missing_schema():
    with pytest.raises(RuntimeError):
        environment.update_config()


@pytest.mark.ckan_config("ckan.site_url", "ftp://demo.ckan.org")
def test_siteurl_wrong_schema():
    with pytest.raises(RuntimeError):
        environment.update_config()


@pytest.mark.ckan_config("ckan.site_url", "http://demo.ckan.org/")
def test_siteurl_removes_backslash(ckan_config):
    environment.update_config()
    assert ckan_config["ckan.site_url"] == "http://demo.ckan.org"


@pytest.mark.ckan_config("ckan.display_timezone", "Krypton/Argo City")
def test_missing_timezone():
    with pytest.raises(CkanConfigurationException):
        environment.update_config()


@pytest.mark.ckan_config("plugin_template_paths", [
    os.path.join(os.path.dirname(__file__), "data")
])
def test_plugin_template_paths_reset(app):
    resp = app.get("/about")
    assert "YOU WILL NOT FIND ME" not in resp


@pytest.mark.ckan_config("SECRET_KEY", "super_secret")
@pytest.mark.ckan_config("beaker.session.secret", None)
@pytest.mark.ckan_config("beaker.session.validate_key", None)
@pytest.mark.ckan_config("WTF_CSRF_SECRET_KEY", None)
def test_all_secrets_default_to_SECRET_KEY(ckan_config):

    environment.update_config()

    for key in [
        "SECRET_KEY",
        "beaker.session.secret",
        "beaker.session.validate_key",
        "WTF_CSRF_SECRET_KEY",
    ]:
        assert ckan_config[key] == "super_secret"

    # Note: api_token.jwt.*.secret are tested in ckan/tests/lib/test_api_token.py
