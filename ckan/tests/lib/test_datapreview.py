# encoding: utf-8

import pytest
from ckan.common import config

import ckan.plugins as p
import ckan.lib.datapreview as datapreview

from ckan.tests import helpers, factories


def test_compare_domains():
    """ see https://en.wikipedia.org/wiki/Same_origin_policy
        """
    compare = datapreview.compare_domains
    assert compare(["http://www.okfn.org", "http://www.okfn.org"])
    assert compare(
        ["http://www.okfn.org", "http://www.okfn.org", "http://www.okfn.org"]
    )
    assert compare(
        [
            "http://www.OKFN.org",
            "http://www.okfn.org",
            "http://www.okfn.org/test/foo.html",
        ]
    )
    assert compare(["http://okfn.org", "http://okfn.org"])
    assert compare(["www.okfn.org", "http://www.okfn.org"])
    assert compare(["//www.okfn.org", "http://www.okfn.org"])
    assert not compare(["http://www.okfn.org", "https://www.okfn.org"])
    assert not compare(["http://www.okfn.org:80", "http://www.okfn.org:81"])

    assert not compare(["http://www.okfn.org", "http://www.okfn.de"])
    assert not compare(["http://de.okfn.org", "http://www.okfn.org"])
    assert not compare(["http://de.okfn.org", "http:www.foo.com"])
    assert not compare(["httpö://wöwöwö.ckan.dö", "www.ckän.örg"])
    assert compare(["www.ckän.örg", "www.ckän.örg"])
    assert not compare(
        [
            "http://Server=cda3; Service=sde:sqlserver:cda3; ",
            "http://www.okf.org",
        ]
    )


class MockDatastoreBasedResourceView(p.SingletonPlugin):

    p.implements(p.IResourceView)

    def info(self):
        return {
            "name": "test_datastore_view",
            "title": "Test Datastore View",
            "requires_datastore": True,
        }


@pytest.mark.ckan_config(
    "ckan.plugins", "image_view datatables_view webpage_view test_datastore_view"
)
@pytest.mark.usefixtures("with_plugins")
class TestDatapreviewWithWebpageView(object):
    def test_no_config(self):

        default_views = datapreview.get_default_view_plugins()

        assert sorted(
            [view_plugin.info()["name"] for view_plugin in default_views]
        ) == ["image_view"]

    def test_no_config_with_datastore_plugins(self):

        default_views = datapreview.get_default_view_plugins(get_datastore_views=True)

        assert sorted(
            [view_plugin.info()["name"] for view_plugin in default_views]
        ) == ["datatables_view"]

    @pytest.mark.ckan_config("ckan.views.default_views", "")
    def test_empty_config(self):
        default_views = datapreview.get_default_view_plugins()
        assert default_views == []

    @pytest.mark.ckan_config("ckan.views.default_views", "image_view")
    def test_in_config(self):

        default_views = datapreview.get_default_view_plugins()

        assert sorted(
            [view_plugin.info()["name"] for view_plugin in default_views]
        ) == ["image_view"]

    @pytest.mark.ckan_config("ckan.views.default_views", "test_datastore_view")
    def test_in_config_datastore_view_only(self):

        default_views = datapreview.get_default_view_plugins(
            get_datastore_views=True
        )

        assert sorted(
            [view_plugin.info()["name"] for view_plugin in default_views]
        ) == ["test_datastore_view"]

    @pytest.mark.ckan_config("ckan.views.default_views", "test_datastore_view")
    def test_in_config_datastore_view_only_with_get_datastore_views(self):

        default_views = datapreview.get_default_view_plugins()

        assert default_views == []

    @pytest.mark.ckan_config(
        "ckan.views.default_views", "image_view test_datastore_view"
    )
    def test_both_plugins_in_config_only_non_datastore(self):
        default_views = datapreview.get_default_view_plugins()

        assert sorted(
            [view_plugin.info()["name"] for view_plugin in default_views]
        ) == ["image_view"]

    @pytest.mark.ckan_config(
        "ckan.views.default_views", "image_view test_datastore_view"
    )
    def test_both_plugins_in_config_only_datastore(self):

        default_views = datapreview.get_default_view_plugins(
            get_datastore_views=True
        )

        assert sorted(
            [view_plugin.info()["name"] for view_plugin in default_views]
        ) == ["test_datastore_view"]


@pytest.mark.ckan_config("ckan.plugins", "image_view test_datastore_view")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
class TestDatapreview(object):
    def test_get_view_plugins(self):

        view_types = ["image_view", "not_there", "test_datastore_view"]

        view_plugins = datapreview.get_view_plugins(view_types)

        assert len(view_plugins) == 2

        assert view_plugins[0].info()["name"] == "image_view"
        assert view_plugins[1].info()["name"] == "test_datastore_view"

    @pytest.mark.ckan_config("ckan.views.default_views", "")
    def test_add_views_to_dataset_resources(self):

        # New resources have no views
        dataset_dict = factories.Dataset(
            resources=[
                {
                    "url": "http://some.image.png",
                    "format": "png",
                    "name": "Image 1",
                },
                {
                    "url": "http://some.image.png",
                    "format": "png",
                    "name": "Image 2",
                },
            ]
        )
        context = {"user": helpers.call_action("get_site_user")["name"]}
        created_views = datapreview.add_views_to_dataset_resources(
            context, dataset_dict, view_types=["image_view"]
        )

        assert len(created_views) == 2

        assert created_views[0]["view_type"] == "image_view"
        assert created_views[1]["view_type"] == "image_view"

    @pytest.mark.ckan_config("ckan.views.default_views", "")
    def test_add_views_to_dataset_resources_no_type_provided(self):

        # New resources have no views
        dataset_dict = factories.Dataset(
            resources=[
                {
                    "url": "http://some.image.png",
                    "format": "png",
                    "name": "Image 1",
                },
                {
                    "url": "http://some.image.png",
                    "format": "png",
                    "name": "Image 2",
                },
            ]
        )

        # Change default views config setting
        config["ckan.views.default_views"] = ["image_view"]

        context = {"user": helpers.call_action("get_site_user")["name"]}
        created_views = datapreview.add_views_to_dataset_resources(
            context, dataset_dict, view_types=[]
        )

        assert len(created_views) == 2

        assert created_views[0]["view_type"] == "image_view"
        assert created_views[1]["view_type"] == "image_view"

    @pytest.mark.ckan_config("ckan.views.default_views", "")
    def test_add_views_to_resource(self):

        resource_dict = factories.Resource(
            url="http://some.image.png", format="png"
        )

        context = {"user": helpers.call_action("get_site_user")["name"]}

        created_views = datapreview.add_views_to_resource(
            context, resource_dict, view_types=["image_view"]
        )

        assert len(created_views) == 1

        assert created_views[0]["view_type"] == "image_view"

    @pytest.mark.ckan_config("ckan.views.default_views", "")
    def test_add_views_to_resource_no_type_provided(self):

        resource_dict = factories.Resource(
            url="http://some.image.png", format="png"
        )

        # Change default views config setting
        config["ckan.views.default_views"] = ["image_view"]

        context = {"user": helpers.call_action("get_site_user")["name"]}
        created_views = datapreview.add_views_to_resource(
            context, resource_dict
        )

        assert len(created_views) == 1

        assert created_views[0]["view_type"] == "image_view"

    @pytest.mark.ckan_config("ckan.views.default_views", "image_view")
    def test_default_views_created_on_package_create(self):

        dataset_dict = factories.Dataset(
            resources=[
                {
                    "url": "http://some.image.png",
                    "format": "png",
                    "name": "Image 1",
                },
                {
                    "url": "http://some.image.png",
                    "format": "png",
                    "name": "Image 2",
                },
            ]
        )

        for resource in dataset_dict["resources"]:
            views_list = helpers.call_action(
                "resource_view_list", id=resource["id"]
            )

            assert len(views_list) == 1
            assert views_list[0]["view_type"] == "image_view"

    @pytest.mark.ckan_config("ckan.views.default_views", "image_view")
    def test_default_views_created_on_resource_create(self):

        dataset_dict = factories.Dataset(
            resources=[{"url": "http://not.for.viewing", "format": "xxx"}]
        )

        resource_dict = {
            "package_id": dataset_dict["id"],
            "url": "http://some.image.png",
            "format": "png",
        }

        new_resource_dict = helpers.call_action(
            "resource_create", **resource_dict
        )

        views_list = helpers.call_action(
            "resource_view_list", id=new_resource_dict["id"]
        )

        assert len(views_list) == 1
        assert views_list[0]["view_type"] == "image_view"
