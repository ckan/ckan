# encoding: utf-8
import pytest

from ckan.common import config, g
from ckan.lib.search import text_traceback


@pytest.mark.ckan_config("solr_user", "solr")
@pytest.mark.ckan_config("solr_password", "password")
def test_solr_user_and_password(app):

    assert config["solr_user"] == "solr"
    assert config["solr_password"] == "password"


def test_text_traceback_dont_fail_on_runtime_error():
    try:
        _ = g.user
    except RuntimeError:
        assert text_traceback()
