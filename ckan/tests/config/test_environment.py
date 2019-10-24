# encoding: utf-8

import os

import pytest

import ckan.plugins as p
from ckan.config import environment
from ckan.exceptions import CkanConfigurationException

ENV_VAR_LIST = [
    (u"CKAN_SQLALCHEMY_URL", u"postgresql://mynewsqlurl/"),
    (u"CKAN_DATASTORE_WRITE_URL", u"http://mynewdbwriteurl/"),
    (u"CKAN_DATASTORE_READ_URL", u"http://mynewdbreadurl/"),
    (u"CKAN_SOLR_URL", u"http://mynewsolrurl/solr"),
    (u"CKAN_SITE_ID", u"my-site"),
    (u"CKAN_DB", u"postgresql://mydeprectatesqlurl/"),
    (u"CKAN_SMTP_SERVER", u"mail.example.com"),
    (u"CKAN_SMTP_STARTTLS", u"True"),
    (u"CKAN_SMTP_USER", u"my_user"),
    (u"CKAN_SMTP_PASSWORD", u"password"),
    (u"CKAN_SMTP_MAIL_FROM", u"server@example.com"),
    (u"CKAN_MAX_UPLOAD_SIZE_MB", u"50"),
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


@pytest.mark.usefixtures(u"reset_env")
def test_update_config_env_vars(ckan_config):
    """
    Setting an env var from the whitelist will set the appropriate option
    in config object.
    """
    for env_var, value in ENV_VAR_LIST:
        os.environ.setdefault(env_var, value)
    # plugin.load() will force the config to update
    p.load()

    assert ckan_config[u"solr_url"] == u"http://mynewsolrurl/solr"
    assert ckan_config[u"sqlalchemy.url"] == u"postgresql://mynewsqlurl/"
    assert (
        ckan_config[u"ckan.datastore.write_url"] == u"http://mynewdbwriteurl/"
    )
    assert ckan_config[u"ckan.datastore.read_url"] == u"http://mynewdbreadurl/"
    assert ckan_config[u"ckan.site_id"] == u"my-site"
    assert ckan_config[u"smtp.server"] == u"mail.example.com"
    assert ckan_config[u"smtp.starttls"] == u"True"
    assert ckan_config[u"smtp.user"] == u"my_user"
    assert ckan_config[u"smtp.password"] == u"password"
    assert ckan_config[u"smtp.mail_from"] == u"server@example.com"
    assert ckan_config[u"ckan.max_resource_size"] == u"50"


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
