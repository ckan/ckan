"""Tests for actions and authorization in ckan/logic/action/resource_view.py."""

import uuid
from unittest import mock

import pytest

from ckan import logic, model
from ckan.common import config
from ckan.tests import factories, helpers


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
class TestResourceViewCreate(object):
    def test_resource_view_create(self):
        context = {}
        params = self._default_resource_view_attributes()

        result = helpers.call_action("resource_view_create", context, **params)

        result.pop("id")
        result.pop("package_id")

        assert params == result

    def test_requires_resource_id(self):
        context = {}
        params = self._default_resource_view_attributes()
        params.pop("resource_id")

        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context, **params)

    def test_requires_title(self):
        context = {}
        params = self._default_resource_view_attributes()
        params.pop("title")

        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context, **params)

    def test_sysadmin_can_set_id(self):
        user = factories.Sysadmin()
        _id = str(uuid.uuid4())
        context = {"user": user["name"], "ignore_auth": False}
        params = self._default_resource_view_attributes()
        params["id"] = _id
        result = helpers.call_action("resource_view_create", context=context, **params)
        assert result["id"] == _id

    def test_normal_user_can_not_set_id(self):
        user = factories.User()
        _id = str(uuid.uuid4())
        context = {"user": user["name"], "ignore_auth": False}
        params = self._default_resource_view_attributes()
        params["id"] = _id
        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context=context, **params)

    def test_id_cant_already_exist(self):
        user = factories.Sysadmin()
        resource_view = factories.ResourceView()
        context = {"user": user["name"], "ignore_auth": False}
        params = self._default_resource_view_attributes()
        params["id"] = resource_view.pop("id")
        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context=context, **params)

    @mock.patch("ckan.lib.datapreview.get_view_plugin")
    def test_requires_view_type(self, get_view_plugin):
        context = {}
        params = self._default_resource_view_attributes()
        params.pop("view_type")

        get_view_plugin.return_value = "mock_view_plugin"

        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context, **params)

    def test_raises_if_couldnt_find_resource(self):
        context = {}
        params = self._default_resource_view_attributes(resource_id="unknown")
        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context, **params)

    def test_raises_if_couldnt_find_view_extension(self):
        context = {}
        params = self._default_resource_view_attributes(view_type="unknown")
        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context, **params)

    @mock.patch("ckan.logic.action.resource_view.datapreview")
    def test_filterable_views_dont_require_any_extra_fields(self, datapreview_mock):
        self._configure_datapreview_to_return_filterable_view(datapreview_mock)
        context = {}
        params = self._default_resource_view_attributes()

        result = helpers.call_action("resource_view_create", context, **params)

        result.pop("id")
        result.pop("package_id")

        assert params == result

    @mock.patch("ckan.logic.action.resource_view.datapreview")
    def test_filterable_views_converts_filter_fields_and_values_into_filters_dict(
        self, datapreview_mock
    ):
        self._configure_datapreview_to_return_filterable_view(datapreview_mock)
        context = {}
        filters = {
            "filter_fields": ["country", "weather", "country"],
            "filter_values": ["Brazil", "warm", "Argentina"],
        }
        params = self._default_resource_view_attributes(**filters)
        result = helpers.call_action("resource_view_create", context, **params)
        expected_filters = {
            "country": ["Brazil", "Argentina"],
            "weather": ["warm"],
        }
        assert result["filters"] == expected_filters

    @mock.patch("ckan.logic.action.resource_view.datapreview")
    def test_filterable_views_converts_filter_fields_and_values_to_list(
        self, datapreview_mock
    ):
        self._configure_datapreview_to_return_filterable_view(datapreview_mock)
        context = {}
        filters = {"filter_fields": "country", "filter_values": "Brazil"}
        params = self._default_resource_view_attributes(**filters)
        result = helpers.call_action("resource_view_create", context, **params)
        assert result["filter_fields"] == ["country"]
        assert result["filter_values"] == ["Brazil"]
        assert result["filters"] == {"country": ["Brazil"]}

    @mock.patch("ckan.logic.action.resource_view.datapreview")
    def test_filterable_views_require_filter_fields_and_values_to_have_same_length(
        self, datapreview_mock
    ):
        self._configure_datapreview_to_return_filterable_view(datapreview_mock)
        context = {}
        filters = {
            "filter_fields": ["country", "country"],
            "filter_values": "Brazil",
        }
        params = self._default_resource_view_attributes(**filters)
        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context, **params)

    def test_non_filterable_views_dont_accept_filter_fields_and_values(self):
        context = {}
        filters = {"filter_fields": "country", "filter_values": "Brazil"}
        params = self._default_resource_view_attributes(**filters)
        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context, **params)

    def _default_resource_view_attributes(self, **kwargs):
        default_attributes = {
            "resource_id": factories.Resource()["id"],
            "view_type": "image_view",
            "title": "View",
            "description": "A nice view",
        }

        default_attributes.update(kwargs)

        return default_attributes

    def _configure_datapreview_to_return_filterable_view(self, datapreview_mock):
        filterable_view = mock.MagicMock()
        filterable_view.info.return_value = {"filterable": True}
        datapreview_mock.get_view_plugin.return_value = filterable_view


@pytest.mark.ckan_config("ckan.views.default_views", "")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_add_default_views_to_dataset_resources():

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

    context = {"user": model.User.get_site_user().name}
    created_views = helpers.call_action(
        "package_create_default_resource_views",
        context,
        package=dataset_dict,
    )

    assert len(created_views) == 2

    assert created_views[0]["view_type"] == "image_view"
    assert created_views[1]["view_type"] == "image_view"


@pytest.mark.ckan_config("ckan.views.default_views", "")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_add_default_views_to_resource():

    # New resources have no views
    dataset_dict = factories.Dataset()
    resource_dict = factories.Resource(
        package_id=dataset_dict["id"],
        url="http://some.image.png",
        format="png",
    )

    # Change default views config setting
    config["ckan.views.default_views"] = ["image_view"]

    context = {"user": model.User.get_site_user().name}
    created_views = helpers.call_action(
        "resource_create_default_resource_views",
        context,
        resource=resource_dict,
        package=dataset_dict,
    )

    assert len(created_views) == 1

    assert created_views[0]["view_type"] == "image_view"


@pytest.mark.ckan_config("ckan.views.default_views", "")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_add_default_views_to_resource_no_dataset_passed():

    # New resources have no views
    dataset_dict = factories.Dataset()
    resource_dict = factories.Resource(
        package_id=dataset_dict["id"],
        url="http://some.image.png",
        format="png",
    )

    # Change default views config setting
    config["ckan.views.default_views"] = ["image_view"]

    context = {"user": model.User.get_site_user().name}
    created_views = helpers.call_action(
        "resource_create_default_resource_views",
        context,
        resource=resource_dict,
    )

    assert len(created_views) == 1

    assert created_views[0]["view_type"] == "image_view"


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_resource_view_delete():
    resource_view = factories.ResourceView()

    params = {"id": resource_view["id"]}

    helpers.call_action("resource_view_delete", context={}, **params)

    with pytest.raises(logic.NotFound):
        helpers.call_action("resource_view_show", context={}, **params)

    # The model object is actually deleted
    resource_view_obj = model.ResourceView.get(resource_view["id"])
    assert resource_view_obj is None


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_delete_no_id_raises_validation_error():

    params = {}

    with pytest.raises(logic.ValidationError):
        helpers.call_action("resource_view_delete", context={}, **params)


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_delete_wrong_id_raises_not_found_error():

    params = {"id": "does_not_exist"}

    with pytest.raises(logic.NotFound):
        helpers.call_action("resource_view_delete", context={}, **params)


@pytest.mark.ckan_config("ckan.plugins", "image_view datatables_view")
@pytest.mark.ckan_config("ckan.views.default_views", "")
@pytest.mark.usefixtures("with_plugins")
def test_resource_view_clear():
    initial = model.Session.query(model.ResourceView).count()

    factories.ResourceView(view_type="image_view")
    factories.ResourceView(view_type="image_view")

    factories.ResourceView(view_type="datatables_view")
    factories.ResourceView(view_type="datatables_view")

    count = model.Session.query(model.ResourceView).count()

    assert count == initial + 4

    helpers.call_action("resource_view_clear", context={})

    count = model.Session.query(model.ResourceView).count()

    assert count == 0


@pytest.mark.ckan_config("ckan.plugins", "image_view datatables_view")
@pytest.mark.ckan_config("ckan.views.default_views", "")
@pytest.mark.usefixtures("with_plugins")
@pytest.mark.usefixtures("clean_db")
def test_resource_view_clear_with_types():

    model.Session.query(model.ResourceView).count()
    factories.ResourceView(view_type="image_view")
    factories.ResourceView(view_type="image_view")

    factories.ResourceView(view_type="datatables_view")
    factories.ResourceView(view_type="datatables_view")

    count = model.Session.query(model.ResourceView).count()

    assert count == 4

    helpers.call_action("resource_view_clear", context={}, view_types=["image_view"])

    view_types = model.Session.query(model.ResourceView.view_type).all()

    assert len(view_types) == 2
    for view_type in view_types:
        assert view_type[0] == "datatables_view"


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_resource_view_show():

    resource = factories.Resource()
    resource_view = {
        "resource_id": resource["id"],
        "view_type": "image_view",
        "title": "View",
        "description": "A nice view",
        "image_url": "url",
    }

    new_view = helpers.call_action("resource_view_create", **resource_view)

    result = helpers.call_action("resource_view_show", id=new_view["id"])

    result.pop("id")
    result.pop("package_id")

    assert result == resource_view


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_resource_view_show_id_missing():

    with pytest.raises(logic.ValidationError):
        helpers.call_action("resource_view_show")


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_resource_view_show_id_not_found():

    with pytest.raises(logic.NotFound):
        helpers.call_action("resource_view_show", id="does_not_exist")


@pytest.mark.ckan_config("ckan.views.default_views", "")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_resource_view_update():
    resource_view = factories.ResourceView()
    params = {
        "id": resource_view["id"],
        "title": "new title",
        "description": "new description",
    }

    result = helpers.call_action("resource_view_update", **params)

    assert result["title"] == params["title"]
    assert result["description"] == params["description"]


@pytest.mark.ckan_config("ckan.views.default_views", "")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
@mock.patch("ckan.logic.action.resource_view.datapreview")
def test_filterable_views_converts_filter_fields_and_values_into_filters_dict(
    datapreview_mock,
):
    filterable_view = mock.MagicMock()
    filterable_view.info.return_value = {"filterable": True}
    datapreview_mock.get_view_plugin.return_value = filterable_view
    resource_view = factories.ResourceView()
    context = {}
    params = {
        "id": resource_view["id"],
        "filter_fields": ["country", "weather", "country"],
        "filter_values": ["Brazil", "warm", "Argentina"],
    }
    result = helpers.call_action("resource_view_update", context, **params)
    expected_filters = {
        "country": ["Brazil", "Argentina"],
        "weather": ["warm"],
    }
    assert result["filters"] == expected_filters


@pytest.mark.ckan_config("ckan.views.default_views", "")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_resource_view_update_requires_id():
    params = {}

    with pytest.raises(logic.ValidationError):
        helpers.call_action("resource_view_update", **params)


@pytest.mark.ckan_config("ckan.views.default_views", "")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_resource_view_update_requires_existing_id():
    params = {"id": "inexistent_id"}

    with pytest.raises(logic.NotFound):
        helpers.call_action("resource_view_update", **params)


@pytest.mark.ckan_config("ckan.views.default_views", "")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_resource_view_list_reorder():
    resource_view_1 = factories.ResourceView(title="View 1")

    resource_id = resource_view_1["resource_id"]

    resource_view_2 = factories.ResourceView(resource_id=resource_id, title="View 2")

    resource_view_list = helpers.call_action("resource_view_list", id=resource_id)

    assert resource_view_list[0]["title"] == "View 1"
    assert resource_view_list[1]["title"] == "View 2"

    # Reorder views

    result = helpers.call_action(
        "resource_view_reorder",
        id=resource_id,
        order=[resource_view_2["id"], resource_view_1["id"]],
    )
    assert result["order"] == [
        resource_view_2["id"],
        resource_view_1["id"],
    ]

    resource_view_list = helpers.call_action("resource_view_list", id=resource_id)

    assert resource_view_list[0]["title"] == "View 2"
    assert resource_view_list[1]["title"] == "View 1"


@pytest.mark.ckan_config("ckan.views.default_views", "")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_resource_view_list_reorder_just_one_id():
    resource_view_1 = factories.ResourceView(title="View 1")

    resource_id = resource_view_1["resource_id"]

    resource_view_2 = factories.ResourceView(resource_id=resource_id, title="View 2")

    # Reorder Views back just by specifying a single view to go first

    result = helpers.call_action(
        "resource_view_reorder",
        id=resource_id,
        order=[resource_view_2["id"]],
    )
    assert result["order"] == [
        resource_view_2["id"],
        resource_view_1["id"],
    ]

    resource_view_list = helpers.call_action("resource_view_list", id=resource_id)

    assert resource_view_list[0]["title"] == "View 2"
    assert resource_view_list[1]["title"] == "View 1"


@pytest.mark.ckan_config("ckan.views.default_views", "")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_calling_with_only_id_doesnt_update_anything():
    resource_view = factories.ResourceView()
    params = {"id": resource_view["id"]}

    result = helpers.call_action("resource_view_update", **params)
    assert result == resource_view
