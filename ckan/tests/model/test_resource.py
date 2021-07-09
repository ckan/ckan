# encoding: utf-8

import pytest

import ckan.model as model
import ckan.tests.factories as factories

Resource = model.Resource


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestResource(object):
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

    def test_resource_count(self):
        """Resource.count() should return a count of instances of Resource
        class"""
        assert Resource.count() == 0
        factories.Resource()
        factories.Resource()
        factories.Resource()
        assert Resource.count() == 3
