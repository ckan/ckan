# encoding: utf-8

import pytest
import ckan.plugins as p


@pytest.mark.ckan_config("ckan.datastore.sqlsearch.enabled", False)
@pytest.mark.usefixtures("ckan_config")
def test_disable_sql_search():
    with p.use_plugin("datastore") as the_plugin:
        with pytest.raises(
            KeyError, match=u"Action 'datastore_search_sql' not found"
        ):
            p.toolkit.get_action("datastore_search_sql")


@pytest.mark.ckan_config("ckan.datastore.sqlsearch.enabled", True)
@pytest.mark.usefixtures("ckan_config")
def test_enabled_sql_search():
    with p.use_plugin("datastore") as the_plugin:
        p.toolkit.get_action("datastore_search_sql")
