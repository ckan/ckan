# encoding: utf-8

import pytest

import ckan.model as model
import ckan.tests.factories as factories

Resource = model.Resource


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestReousrce(object):
    def test_edit_url(self):
        res_dict = factories.Resource(url="http://first")
        res = Resource.get(res_dict["id"])
        res.url = "http://second"
        model.repo.commit_and_remove()
        res = Resource.get(res_dict["id"])
        assert res.url == "http://second"

    def test_edit_extra(self):
        res_dict = factories.Resource(newfield="first")
        res = Resource.get(res_dict["id"])
        res.extras = {"newfield": "second"}
        model.repo.commit_and_remove()
        res = Resource.get(res_dict["id"])
        assert res.extras["newfield"] == "second"

    def test_get_all_without_views_returns_all_resources_without_views(self):
        # Create resource with resource_view
        factories.ResourceView()

        expected_resources = [
            factories.Resource(format="format"),
            factories.Resource(format="other_format"),
        ]

        resources = Resource.get_all_without_views()

        expected_resources_ids = [r["id"] for r in expected_resources]
        resources_ids = [r.id for r in resources]

        assert expected_resources_ids.sort() == resources_ids.sort()

    def test_get_all_without_views_accepts_list_of_formats_ignoring_case(self):
        factories.Resource(format="other_format")
        resource_id = factories.Resource(format="format")["id"]

        resources = Resource.get_all_without_views(["FORMAT"])

        length = len(resources)
        assert length == 1, "Expected 1 resource, but got %d" % length
        assert [resources[0].id] == [resource_id]

    def test_resource_count(self):
        """Resource.count() should return a count of instances of Resource
        class"""
        assert Resource.count() == 0
        factories.Resource()
        factories.Resource()
        factories.Resource()
        assert Resource.count() == 3
