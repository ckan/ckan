# encoding: utf-8
import pytest

from ckan.common import config


@pytest.mark.ckan_config("solr_user", "solr")
@pytest.mark.ckan_config("solr_password", "password")
def test_solr_user_and_password(app):

    assert config["solr_user"] == "solr"
    assert config["solr_password"] == "password"
