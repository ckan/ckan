# encoding: utf-8

import os

import pytest

import ckan.plugins as p
from ckan.config import environment
from ckan.exceptions import CkanConfigurationException

ENV_VAR_LIST = [
    ("CKAN_SQLALCHEMY_URL", "postgresql://mynewsqlurl/"),
    ("CKAN_DATASTORE_WRITE_URL", "http://mynewdbwriteurl/"),
    ("CKAN_DATASTORE_READ_URL", "http://mynewdbreadurl/"),
    ("CKAN_SOLR_URL", "http://mynewsolrurl/solr"),
    ("CKAN_SITE_ID", "my-site"),
    ("CKAN_DB", "postgresql://mydeprectatesqlurl/"),
    ("CKAN_SMTP_SERVER", "mail.example.com"),
    ("CKAN_SMTP_STARTTLS", "True"),
    ("CKAN_SMTP_USER", "my_user"),
    ("CKAN_SMTP_PASSWORD", "password"),
    ("CKAN_SMTP_MAIL_FROM", "server@example.com"),
    ("CKAN_MAX_UPLOAD_SIZE_MB", "50"),
]


@pytest.fixture
def reset_env():
    """Reset all environment variables that were patched during tests.

    """
    yield
    for env_var, _ in ENV_VAR_LIST:
        if os.environ.get(env_var, None):
            del os.environ[env_var]
    p.load()


@pytest.mark.usefixtures("reset_env")
def test_update_config_env_vars(ckan_config):
    """
    Setting an env var from the whitelist will set the appropriate option
    in config object.
    """
    for env_var, value in ENV_VAR_LIST:
        os.environ.setdefault(env_var, value)
    # plugin.load() will force the config to update
    p.load()

    assert ckan_config["solr_url"] == "http://mynewsolrurl/solr"
    assert ckan_config["sqlalchemy.url"] == "postgresql://mynewsqlurl/"
    assert (
        ckan_config["ckan.datastore.write_url"] == "http://mynewdbwriteurl/"
    )
    assert ckan_config["ckan.datastore.read_url"] == "http://mynewdbreadurl/"
    assert ckan_config["ckan.site_id"] == "my-site"
    assert ckan_config["smtp.server"] == "mail.example.com"
    assert ckan_config["smtp.starttls"] == "True"
    assert ckan_config["smtp.user"] == "my_user"
    assert ckan_config["smtp.password"] == "password"
    assert ckan_config["smtp.mail_from"] == "server@example.com"
    assert ckan_config["ckan.max_resource_size"] == "50"


@pytest.mark.usefixtures("reset_env")
def test_update_config_db_url_precedence(ckan_config):
    """CKAN_SQLALCHEMY_URL in the env takes precedence over CKAN_DB"""
    os.environ.setdefault("CKAN_DB", "postgresql://mydeprectatesqlurl/")
    os.environ.setdefault("CKAN_SQLALCHEMY_URL", "postgresql://mynewsqlurl/")
    p.load()

    assert ckan_config["sqlalchemy.url"] == "postgresql://mynewsqlurl/"


@pytest.mark.ckan_config("ckan.site_url", "")
def test_missing_siteurl():
    with pytest.raises(RuntimeError):
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
