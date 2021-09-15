# encoding: utf-8
import pytest

from ckan.common import config


@pytest.mark.ckan_config(u"solr_user", u"solr")
@pytest.mark.ckan_config(u"solr_password", u"password")
def test_solr_user_and_password(app):

    assert config[u"solr_user"] == u"solr"
    assert config[u"solr_password"] == u"password"
