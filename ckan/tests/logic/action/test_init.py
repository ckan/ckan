# -*- coding: utf-8 -*-

import pytest
import ckan.model as model
import ckan.logic as logic
import ckan.plugins as p
from ckan.logic.action import get_domain_object
from ckan.tests import factories, helpers


@pytest.mark.usefixtures("clean_db")
def test_32_get_domain_object():
    pkg = factories.Dataset()
    group = factories.Group()
    assert get_domain_object(model, pkg["name"]).name == pkg["name"]
    assert get_domain_object(model, pkg["id"]).name == pkg["name"]

    assert get_domain_object(model, group["name"]).name == group["name"]
    assert get_domain_object(model, group["id"]).name == group["name"]


def test_41_missing_action():
    with pytest.raises(KeyError):
        logic.get_action("unicorns")


class MockPackageSearchPlugin(p.SingletonPlugin):
    p.implements(p.IPackageController, inherit=True)

    def before_index(self, data_dict):
        data_dict["extras_test"] = "abcabcabc"
        return data_dict

    def before_search(self, search_params):
        if (
            "extras" in search_params
            and "ext_avoid" in search_params["extras"]
        ):
            assert "q" in search_params

        if (
            "extras" in search_params
            and "ext_abort" in search_params["extras"]
        ):
            assert "q" in search_params
            # Prevent the actual query
            search_params["abort_search"] = True

        return search_params

    def after_search(self, search_results, search_params):

        assert "results" in search_results
        assert "count" in search_results
        assert "search_facets" in search_results

        if (
            "extras" in search_params
            and "ext_avoid" in search_params["extras"]
        ):
            # Remove results with a certain value
            avoid = search_params["extras"]["ext_avoid"]

            for i, result in enumerate(search_results["results"]):
                if (
                    avoid.lower() in result["name"].lower()
                    or avoid.lower() in result["title"].lower()
                ):
                    search_results["results"].pop(i)
                    search_results["count"] -= 1

        return search_results

    def before_view(self, data_dict):
        data_dict["title"] = "string_not_found_in_rest_of_template"
        return data_dict


@pytest.mark.ckan_config("ckan.plugins", "mock_search_plugin")
@pytest.mark.usefixtures("clean_db", "clean_index", "with_plugins")
class TestSearchPluginInterface(object):
    def test_search_plugin_interface_search(self):
        avoid = "Tolstoy"
        factories.Dataset(title=avoid)
        result = helpers.call_action(
            "package_search", q="*:*", extras={"ext_avoid": avoid}
        )
        assert result["count"] == 0

    def test_search_plugin_interface_abort(self):
        factories.Dataset()
        result = helpers.call_action(
            "package_search", q="*:*", extras={"ext_abort": True}
        )
        assert result["count"] == 0

    def test_before_index(self):
        factories.Dataset()
        factories.Dataset()
        result = helpers.call_action("package_search", q="aaaaaaaa")
        assert result["count"] == 0

        # all datasets should get abcabcabc
        result = helpers.call_action("package_search", q="abcabcabc")
        assert result["count"] == 2

    def test_before_view(self, app):
        pkg = factories.Dataset()
        pkg = factories.Dataset()

        res = app.get("/dataset/" + pkg["id"])
        assert "string_not_found_in_rest_of_template" in res

        res = app.get("/dataset?q=")
        assert str(res.body).count("string_not_found_in_rest_of_template") == 2
