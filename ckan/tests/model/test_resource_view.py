# encoding: utf-8

import pytest

import ckan.model as model
import ckan.tests.factories as factories

ResourceView = model.ResourceView


@pytest.mark.ckan_config("ckan.plugins", "image_view webpage_view")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
class TestResourceView(object):
    def test_resource_view_get(self):
        resource_view_id = factories.ResourceView()["id"]
        resource_view = ResourceView.get(resource_view_id)

        assert resource_view is not None

    @pytest.mark.usefixtures("clean_db")
    def test_get_count_view_type(self):
        factories.ResourceView(view_type="image_view")
        factories.ResourceView(view_type="webpage_view")

        result = ResourceView.get_count_not_in_view_types(["image_view"])

        assert result == [("webpage_view", 1)]

    @pytest.mark.usefixtures("clean_db")
    def test_delete_view_type(self):
        factories.ResourceView(view_type="image_view")
        factories.ResourceView(view_type="webpage_view")

        ResourceView.delete_not_in_view_types(["image_view"])

        result = ResourceView.get_count_not_in_view_types(["image_view"])
        assert result == []

    @pytest.mark.usefixtures("clean_db")
    def test_delete_view_type_doesnt_commit(self):
        factories.ResourceView(view_type="image_view")
        factories.ResourceView(view_type="webpage_view")

        ResourceView.delete_not_in_view_types(["image_view"])
        model.Session.rollback()

        result = ResourceView.get_count_not_in_view_types(["image_view"])
        assert result == [("webpage_view", 1)]

    def test_purging_resource_removes_its_resource_views(self):
        resource_view_dict = factories.ResourceView()
        resource = model.Resource.get(resource_view_dict["resource_id"])

        resource.purge()
        model.repo.commit_and_remove()

        assert ResourceView.get(resource_view_dict["id"]) is None
