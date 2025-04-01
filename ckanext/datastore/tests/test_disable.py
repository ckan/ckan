# encoding: utf-8

import pytest
import ckan.plugins as p


@pytest.mark.ckan_config("ckan.datastore.sqlsearch.enabled", None)
@pytest.mark.usefixtures("with_plugins")
def test_disabled_by_default():
    with p.use_plugin("datastore"):
        with pytest.raises(
            KeyError, match=u"Action 'datastore_search_sql' not found"
        ):
            p.toolkit.get_action("datastore_search_sql")


@pytest.mark.ckan_config("ckan.datastore.sqlsearch.enabled", False)
@pytest.mark.usefixtures("with_plugins")
def test_disable_sql_search():
    with p.use_plugin("datastore"):
        with pytest.raises(
            KeyError, match=u"Action 'datastore_search_sql' not found"
        ):
            p.toolkit.get_action("datastore_search_sql")


@pytest.mark.ckan_config("ckan.datastore.sqlsearch.enabled", True)
@pytest.mark.usefixtures("with_plugins")
def test_enabled_sql_search():
    with p.use_plugin("datastore"):
        p.toolkit.get_action("datastore_search_sql")
