"""Tests for actions and authorization in ckan/logic/action/resource.py."""

import datetime
import re
import unittest.mock as mock
import uuid

import pytest
from freezegun import freeze_time

import ckan.lib.uploader as uploader
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as p
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan.lib import files
from ckan.logic.action.package import package_show as core_package_show


@pytest.mark.usefixtures("non_clean_db")
def test_resource_create():
    context = {}
    params = {
        "package_id": factories.Dataset()["id"],
        "url": "http://data",
        "name": "A nice resource",
    }
    result = helpers.call_action("resource_create", context, **params)

    id = result.pop("id")

    assert id

    params.pop("package_id")
    for key in params.keys():
        assert params[key] == result[key]


@pytest.mark.usefixtures("non_clean_db")
def test_it_requires_package_id():

    data_dict = {"url": "http://data"}

    with pytest.raises(logic.ValidationError):
        helpers.call_action("resource_create", **data_dict)


@pytest.mark.usefixtures("non_clean_db")
def test_invalid_characters_in_id():

    data_dict = {
        "id": "../../nope.txt",
        "package_id": factories.Dataset()["id"],
        "url": "http://data",
        "name": "A nice resource",
    }

    with pytest.raises(logic.ValidationError):
        helpers.call_action("resource_create", **data_dict)


@pytest.mark.usefixtures("non_clean_db")
def test_id_too_long():

    data_dict = {
        "id": "x" * 111,
        "package_id": factories.Dataset()["id"],
        "url": "http://data",
        "name": "A nice resource",
    }

    with pytest.raises(logic.ValidationError):
        helpers.call_action("resource_create", **data_dict)


@pytest.mark.usefixtures("non_clean_db")
def test_id_already_exists():
    data_dict = {
        "id": str(uuid.uuid4()),
        "package_id": factories.Dataset()["id"],
    }
    helpers.call_action("resource_create", **data_dict)

    data_dict["package_id"] = factories.Dataset()["id"]

    with pytest.raises(logic.ValidationError):
        helpers.call_action("resource_create", **data_dict)


@pytest.mark.usefixtures("non_clean_db")
def test_sysadmin_can_set_id():
    """
    The system admin
    """
    user = factories.Sysadmin()
    context = {"user": user["name"], "ignore_auth": False}
    _id = str(uuid.uuid4())
    data_dict = {
        "id": _id,
        "package_id": factories.Dataset()["id"],
        "url": "http://data",
        "name": "A nice resource",
    }

    result = helpers.call_action("resource_create", context=context, **data_dict)
    assert result["id"] == _id


@pytest.mark.usefixtures("non_clean_db")
def test_normal_user_can_provide_custom_id():

    user = factories.User()
    context = {"user": user["name"], "ignore_auth": False}
    _id = str(uuid.uuid4())
    data_dict = {
        "id": _id,
        "package_id": factories.Dataset()["id"],
        "url": "http://data",
        "name": "A nice resource",
    }
    result = helpers.call_action("resource_create", context=context, **data_dict)
    assert result["id"] == _id


@pytest.mark.usefixtures("non_clean_db")
def test_doesnt_require_url():
    dataset = factories.Dataset()
    data_dict = {"package_id": dataset["id"]}
    new_resouce = helpers.call_action("resource_create", **data_dict)

    data_dict = {"id": new_resouce["id"]}
    stored_resource = helpers.call_action("resource_show", **data_dict)

    assert not stored_resource["url"]


@pytest.mark.usefixtures("non_clean_db")
def test_mimetype_by_url():
    """The mimetype is guessed from the url

    Real world usage would be externally linking the resource and
    the mimetype would be guessed, based on the url

    """
    context = {}
    params = {
        "package_id": factories.Dataset()["id"],
        "url": "http://localhost/data.csv",
        "name": "A nice resource",
    }
    result = helpers.call_action("resource_create", context, **params)

    mimetype = result.pop("mimetype")

    assert mimetype
    assert mimetype == "text/csv"


@pytest.mark.usefixtures("non_clean_db")
def test_mimetype_by_url_without_path():
    """
    The mimetype should not be guessed from url if url contains only domain

    """
    context = {}
    params = {
        "package_id": factories.Dataset()["id"],
        "url": "http://example.com",
        "name": "A nice resource",
    }
    result = helpers.call_action("resource_create", context, **params)

    mimetype = result.pop("mimetype")
    assert mimetype is None


@pytest.mark.usefixtures("non_clean_db")
def test_mimetype_by_user():
    """
    The mimetype is supplied by the user

    Real world usage would be using the FileStore API or web UI form to create a resource
    and the user wanted to specify the mimetype themselves
    """
    context = {}
    params = {
        "package_id": factories.Dataset()["id"],
        "url": "http://localhost/data.csv",
        "name": "A nice resource",
        "mimetype": "application/csv",
    }
    result = helpers.call_action("resource_create", context, **params)

    mimetype = result.pop("mimetype")
    assert mimetype == "application/csv"


@pytest.mark.usefixtures("non_clean_db")
def test_mimetype_by_upload_by_filename(create_with_upload):
    """The mimetype is guessed from an uploaded file with a filename

    Real world usage would be using the FileStore API or web UI
    form to upload a file, with a filename plus extension If
    there's no url or the mimetype can't be guessed by the url,
    mimetype will be guessed by the extension in the filename

    """
    content = """
    "info": {
        "title": "BC Data Catalogue API",
        "description": "This API provides information about datasets in the BC Data Catalogue.",
        "termsOfService": "http://www.data.gov.bc.ca/local/dbc/docs/license/API_Terms_of_Use.pdf",
        "contact": {
            "name": "Data BC",
            "url": "http://data.gov.bc.ca/",
            "email": ""
        },
        "license": {
            "name": "Open Government License - British Columbia",
            "url": "http://www.data.gov.bc.ca/local/dbc/docs/license/OGL-vbc2.0.pdf"
        },
        "version": "3.0.0"
    }
    """

    result = create_with_upload(
        content,
        "test.json",
        url="http://data",
        package_id=factories.Dataset()["id"],
    )
    mimetype = result.pop("mimetype")

    assert mimetype
    assert mimetype == "application/json"


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.mimetype_guess", "file_contents")
def test_mimetype_by_upload_by_file(create_with_upload):
    """The mimetype is guessed from an uploaded file by the contents inside

    Real world usage would be using the FileStore API or web UI
    form to upload a file, that has no extension If the mimetype
    can't be guessed by the url or filename, mimetype will be
    guessed by the contents inside the file

    """

    content = """
    Snow Course Name, Number, Elev. metres, Date of Survey, Snow Depth cm,\
    Water Equiv. mm, Survey Code, % of Normal, Density %, Survey Period, \
    Normal mm
    SKINS LAKE,1B05,890,2015/12/30,34,53,,98,16,JAN-01,54
    MCGILLIVRAY PASS,1C05,1725,2015/12/31,88,239,,87,27,JAN-01,274
    NAZKO,1C08,1070,2016/01/05,20,31,,76,16,JAN-01,41
    """
    result = create_with_upload(
        content,
        "test.csv",
        url="http://data",
        package_id=factories.Dataset()["id"],
    )

    mimetype = result.pop("mimetype")

    assert mimetype
    assert mimetype == "text/plain"


@pytest.mark.usefixtures("non_clean_db")
def test_size_of_resource_by_upload(create_with_upload):
    """
    The size of the resource determined by the uploaded file
    """

    content = """
    Snow Course Name, Number, Elev. metres, Date of Survey, Snow Depth cm,\
    Water Equiv. mm, Survey Code, % of Normal, Density %, Survey Period, \
    Normal mm
    SKINS LAKE,1B05,890,2015/12/30,34,53,,98,16,JAN-01,54
    MCGILLIVRAY PASS,1C05,1725,2015/12/31,88,239,,87,27,JAN-01,274
    NAZKO,1C08,1070,2016/01/05,20,31,,76,16,JAN-01,41
    """
    result = create_with_upload(
        content,
        "test.csv",
        url="http://data",
        package_id=factories.Dataset()["id"],
    )

    size = result.pop("size")

    assert size
    assert size > 0


@pytest.mark.usefixtures("non_clean_db")
def test_size_of_resource_by_user():
    """
    The size of the resource is provided by the users

    Real world usage would be using the FileStore API and the user provides a size for the resource
    """
    context = {}
    params = {
        "package_id": factories.Dataset()["id"],
        "url": "http://data",
        "name": "A nice resource",
        "size": 500,
    }
    result = helpers.call_action("resource_create", context, **params)

    size = int(result.pop("size"))
    assert size == 500


@pytest.mark.usefixtures("non_clean_db")
def test_extras():
    user = factories.User()
    dataset = factories.Dataset(user=user)

    resource = helpers.call_action(
        "resource_create",
        package_id=dataset["id"],
        somekey="somevalue",  # this is how to do resource extras
        extras={"someotherkey": "alt234"},  # this isn't
        subobject={"hello": "there"},  # JSON objects supported
        sublist=[1, 2, 3],  # JSON lists supported
        format="plain text",
        url="http://datahub.io/download/",
    )

    assert resource["somekey"] == "somevalue"
    assert "extras" not in resource
    assert "someotherkey" not in resource
    assert resource["subobject"] == {"hello": "there"}
    assert resource["sublist"] == [1, 2, 3]
    resource = helpers.call_action("package_show", id=dataset["id"])["resources"][0]
    assert resource["somekey"] == "somevalue"
    assert "extras" not in resource
    assert "someotherkey" not in resource
    assert resource["subobject"] == {"hello": "there"}
    assert resource["sublist"] == [1, 2, 3]


@pytest.mark.usefixtures("non_clean_db")
@freeze_time("2020-02-25 12:00:00")
def test_metadata_modified_is_set_to_utcnow_when_created():
    context = {}
    params = {
        "package_id": factories.Dataset()["id"],
        "url": "http://data",
        "name": "A nice resource",
    }
    result = helpers.call_action("resource_create", context, **params)

    assert result["metadata_modified"] == datetime.datetime.utcnow().isoformat()


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
@pytest.mark.ckan_config("ckan.auth.allow_admin_collaborators", True)
@pytest.mark.parametrize("role", ["admin", "editor"])
def test_collaborators_can_create_resources(role):

    org1 = factories.Organization()
    dataset = factories.Dataset(owner_org=org1["id"])

    user = factories.User()

    helpers.call_action(
        "package_collaborator_create",
        id=dataset["id"],
        user_id=user["id"],
        capacity=role,
    )

    context = {
        "user": user["name"],
        "ignore_auth": False,
    }

    created_resource = helpers.call_action(
        "resource_create",
        context=context,
        package_id=dataset["id"],
        name="created by collaborator",
        url="https://example.com",
    )

    assert created_resource["name"] == "created by collaborator"


@pytest.mark.usefixtures("non_clean_db")
def test_resource_create_for_update():

    dataset = factories.Dataset()

    mock_package_show = mock.MagicMock()
    mock_package_show.side_effect = lambda context, data_dict: core_package_show(
        context, data_dict
    )

    with mock.patch.dict("ckan.logic._actions", {"package_show": mock_package_show}):
        helpers.call_action(
            "resource_create",
            package_id=dataset["id"],
            url="http://example.com",
            description="hey",
        )
        assert mock_package_show.call_args_list[0][0][0].get("for_update") is True


@pytest.mark.usefixtures("non_clean_db")
def test_resource_create_copies_other_resources():
    from ckan.lib.dictization import model_save

    existing = factories.Resource()
    params = {
        "package_id": existing["package_id"],
        "url": "http://data",
        "name": "A second resource",
    }
    with mock.patch(
        "ckan.lib.dictization.model_save.package_dict_save",
        wraps=model_save.package_dict_save,
    ) as m:
        helpers.call_action("resource_create", **params)
        assert m.call_args.args[3] == {0: 0}, "copy existing resource 0"


@pytest.mark.usefixtures("non_clean_db")
def test_upload_file_paths(create_with_upload):
    storage = files.get_storage("resources")
    dataset = factories.Dataset()
    resource1 = create_with_upload(
        "hello world", "file1.txt", url="http://data1", package_id=dataset["id"]
    )

    id = resource1["id"]
    location = f"{id[:3]}/{id[3:6]}/{id[6:]}"
    assert storage.exists(files.FileData.from_string(location))

    resource2 = create_with_upload(
        "bye bye world", "file2.txt", url="http://data2", package_id=dataset["id"]
    )

    id = resource2["id"]
    location = f"{id[:3]}/{id[3:6]}/{id[6:]}"
    assert storage.exists(files.FileData.from_string(location))


@pytest.mark.usefixtures("non_clean_db")
def test_resource_delete():
    user = factories.User()
    sysadmin = factories.Sysadmin()
    resource = factories.Resource(user=user)
    context = {}
    params = {"id": resource["id"]}

    helpers.call_action("resource_delete", context, **params)

    # Not even a sysadmin can see it now
    with pytest.raises(logic.NotFound):
        helpers.call_action("resource_show", {"user": sysadmin["name"]}, **params)
    # It is still there but with state=deleted
    res_obj = model.Resource.get(resource["id"])
    assert res_obj.state == "deleted"


@pytest.mark.usefixtures("non_clean_db")
def test_resource_delete_for_delete():

    dataset = factories.Dataset()
    resource = factories.Resource(package_id=dataset["id"])

    mock_package_show = mock.MagicMock()
    mock_package_show.side_effect = lambda context, data_dict: core_package_show(
        context, data_dict
    )

    with mock.patch.dict("ckan.logic._actions", {"package_show": mock_package_show}):
        helpers.call_action("resource_delete", id=resource["id"], description="hey")
        assert mock_package_show.call_args_list[1][0][0].get("for_update") is True


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
@pytest.mark.ckan_config("ckan.auth.allow_admin_collaborators", True)
@pytest.mark.parametrize("role", ["admin", "editor"])
def test_collaborators_can_delete_resources(role):

    org1 = factories.Organization()
    dataset = factories.Dataset(owner_org=org1["id"])
    resource = factories.Resource(package_id=dataset["id"])

    user = factories.User()

    helpers.call_action(
        "package_collaborator_create",
        id=dataset["id"],
        user_id=user["id"],
        capacity=role,
    )

    context = {
        "user": user["name"],
        "ignore_auth": False,
    }

    helpers.call_action("resource_delete", context=context, id=resource["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_01_delete_resource():
    res = factories.Resource()
    pkg = helpers.call_action("package_show", id=res["package_id"])
    assert len(pkg["resources"]) == 1
    helpers.call_action("resource_delete", id=res["id"])
    pkg = helpers.call_action("package_show", id=res["package_id"])
    assert len(pkg["resources"]) == 0


@pytest.mark.usefixtures("non_clean_db")
def test_resource_delete_copies_other_resources():
    from ckan.lib.dictization import model_save

    res1 = factories.Resource()
    res2 = factories.Resource(package_id=res1["package_id"])
    factories.Resource(package_id=res1["package_id"])
    params = {
        "id": res2["id"],
    }
    with mock.patch(
        "ckan.lib.dictization.model_save.package_dict_save",
        wraps=model_save.package_dict_save,
    ) as m:
        helpers.call_action("resource_delete", **params)
        assert m.call_args.args[3] == {0: 0, 1: 2}, "unchanged res 0, 2"


@pytest.mark.usefixtures("clean_db")
def test_required_fields():
    with pytest.raises(logic.ValidationError):
        helpers.call_action("resource_search")
    helpers.call_action("resource_search", query="name:*")


@pytest.mark.usefixtures("clean_db")
def test_base_search():
    factories.Resource(name="one")
    factories.Resource(name="two")
    result = helpers.call_action("resource_search", query="name:three")
    assert not result["count"]

    result = helpers.call_action("resource_search", query="name:one")
    assert result["count"] == 1

    result = helpers.call_action("resource_search", query="name:")
    assert result["count"] == 2


@pytest.mark.usefixtures("clean_db")
def test_date_search():
    res = factories.Resource()
    result = helpers.call_action("resource_search", query="created:" + res["created"])
    assert result["count"] == 1


@pytest.mark.usefixtures("clean_db")
def test_number_search():
    factories.Resource(size=10)
    result = helpers.call_action("resource_search", query="size:10")
    assert result["count"] == 1


@pytest.mark.usefixtures("clean_db")
def test_resource_search_across_multiple_fields():
    factories.Resource(description="indexed resource", format="json")
    result = helpers.call_action(
        "resource_search", query=["description:index", "format:json"]
    )
    assert result["count"] == 1
    resource = result["results"][0]
    assert "index" in resource["description"].lower()
    assert "json" in resource["format"].lower()


@pytest.mark.usefixtures("clean_db")
def test_resource_search_test_percentage_is_escaped():
    factories.Resource(description="indexed resource", format="json")
    result = helpers.call_action("resource_search", query="description:index%")
    assert result == {"count": 0, "results": []}


@pytest.mark.usefixtures("non_clean_db")
def test_resource_patch_updating_single_field():
    user = factories.User()
    dataset = factories.Dataset(
        notes="some test now",
        user=user,
        resources=[{"url": "http://example.com/resource"}],
    )

    resource = helpers.call_action(
        "resource_patch",
        id=dataset["resources"][0]["id"],
        name="somethingnew",
    )

    assert resource["name"] == "somethingnew"
    assert resource["url"] == "http://example.com/resource"

    dataset2 = helpers.call_action("package_show", id=dataset["id"])

    resource2 = dataset2["resources"][0]
    assert resource2["name"] == "somethingnew"
    assert resource2["url"] == "http://example.com/resource"


@pytest.mark.usefixtures("non_clean_db")
def test_resource_patch_for_update():

    dataset = factories.Dataset()
    resource = factories.Resource(package_id=dataset["id"])

    mock_package_show = mock.MagicMock()
    mock_package_show.side_effect = lambda context, data_dict: core_package_show(
        context, data_dict
    )

    with mock.patch.dict("ckan.logic._actions", {"package_show": mock_package_show}):
        helpers.call_action("resource_patch", id=resource["id"], description="hey")
        assert mock_package_show.call_args_list[0][0][0].get("for_update") is True


@pytest.mark.usefixtures("non_clean_db")
def test_resource_patch_copies_other_resources():
    from ckan.lib.dictization import model_save

    res1 = factories.Resource()
    res2 = factories.Resource(
        package_id=res1["package_id"],
        url="http://data",
    )
    params = {
        "id": res2["id"],
        "url": "http://data2",
    }
    with mock.patch(
        "ckan.lib.dictization.model_save.package_dict_save",
        wraps=model_save.package_dict_save,
    ) as m:
        helpers.call_action("resource_patch", **params)
        assert m.call_args.args[3] == {0: 0}, "res 0 unmodified"


@pytest.mark.usefixtures("non_clean_db")
class TestUpdateResource(object):
    def teardown(self):
        # Since some of the test methods below use the mock module to patch
        # things, we use this teardown() method to remove remove all patches.
        # (This makes sure the patches always get removed even if the test
        # method aborts with an exception or something.)
        mock.patch.stopall()

    def test_resource_reorder(self):
        resource_urls = ["http://a.html", "http://b.html", "http://c.html"]
        dataset = {
            "name": "basic",
            "resources": [{"url": url} for url in resource_urls],
        }

        dataset = helpers.call_action("package_create", **dataset)
        created_resource_urls = [resource["url"] for resource in dataset["resources"]]
        assert created_resource_urls == resource_urls
        mapping = dict(
            (resource["url"], resource["id"]) for resource in dataset["resources"]
        )

        # This should put c.html at the front
        reorder = {"id": dataset["id"], "order": [mapping["http://c.html"]]}

        from ckan.lib.dictization import model_save

        with mock.patch(
            "ckan.lib.dictization.model_save.package_dict_save",
            wraps=model_save.package_dict_save,
        ) as m:
            helpers.call_action("package_resource_reorder", **reorder)
            assert m.call_args.args[3] == {0: 2, 1: 0, 2: 1}, "move existing"

        dataset = helpers.call_action("package_show", id=dataset["id"])
        reordered_resource_urls = [resource["url"] for resource in dataset["resources"]]

        assert reordered_resource_urls == [
            "http://c.html",
            "http://a.html",
            "http://b.html",
        ]

        reorder = {
            "id": dataset["id"],
            "order": [
                mapping["http://b.html"],
                mapping["http://c.html"],
                mapping["http://a.html"],
            ],
        }

        helpers.call_action("package_resource_reorder", **reorder)
        dataset = helpers.call_action("package_show", id=dataset["id"])

        reordered_resource_urls = [resource["url"] for resource in dataset["resources"]]

        assert reordered_resource_urls == [
            "http://b.html",
            "http://c.html",
            "http://a.html",
        ]


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_url_only():
    resource = factories.Resource(url="http://first")

    res_returned = helpers.call_action(
        "resource_update", id=resource["id"], url="http://second"
    )

    assert res_returned["url"] == "http://second"
    resource = helpers.call_action("resource_show", id=resource["id"])
    assert resource["url"] == "http://second"


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_extra_only():
    resource = factories.Resource(newfield="first")

    res_returned = helpers.call_action(
        "resource_update",
        id=resource["id"],
        url=resource["url"],
        newfield="second",
    )

    assert res_returned["newfield"] == "second"
    resource = helpers.call_action("resource_show", id=resource["id"])
    assert resource["newfield"] == "second"


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_both_extra_and_url():
    resource = factories.Resource(url="http://first", newfield="first")

    res_returned = helpers.call_action(
        "resource_update",
        id=resource["id"],
        url="http://second",
        newfield="second",
    )

    assert res_returned["url"] == "http://second"
    assert res_returned["newfield"] == "second"

    resource = helpers.call_action("resource_show", id=resource["id"])
    assert res_returned["url"] == "http://second"
    assert resource["newfield"] == "second"


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_extra_gets_deleted_on_both_core_and_extra_update():
    resource = factories.Resource(url="http://first", newfield="first")

    res_returned = helpers.call_action(
        "resource_update",
        id=resource["id"],
        url="http://second",
        anotherfield="second",
    )

    assert res_returned["url"] == "http://second"
    assert res_returned["anotherfield"] == "second"
    assert "newfield" not in res_returned

    resource = helpers.call_action("resource_show", id=resource["id"])
    assert res_returned["url"] == "http://second"
    assert res_returned["anotherfield"] == "second"
    assert "newfield" not in res_returned


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_extra_gets_deleted_on_extra_only_update():
    resource = factories.Resource(url="http://first", newfield="first")

    res_returned = helpers.call_action(
        "resource_update",
        id=resource["id"],
        url="http://first",
        anotherfield="second",
    )

    assert res_returned["url"] == "http://first"
    assert res_returned["anotherfield"] == "second"
    assert "newfield" not in res_returned

    resource = helpers.call_action("resource_show", id=resource["id"])
    assert res_returned["url"] == "http://first"
    assert res_returned["anotherfield"] == "second"
    assert "newfield" not in res_returned


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_datastore_active_is_persisted_if_true_and_not_provided():
    resource = factories.Resource(url="http://example.com", datastore_active=True)

    res_returned = helpers.call_action(
        "resource_update",
        id=resource["id"],
        url="http://example.com",
        name="Test",
    )

    assert res_returned["datastore_active"]


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_datastore_active_is_persisted_if_false_and_not_provided():
    resource = factories.Resource(url="http://example.com", datastore_active=False)

    res_returned = helpers.call_action(
        "resource_update",
        id=resource["id"],
        url="http://example.com",
        name="Test",
    )

    assert not res_returned["datastore_active"]


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_datastore_active_is_updated_if_false_and_provided():
    resource = factories.Resource(url="http://example.com", datastore_active=False)

    res_returned = helpers.call_action(
        "resource_update",
        id=resource["id"],
        url="http://example.com",
        name="Test",
        datastore_active=True,
    )

    assert res_returned["datastore_active"]


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_datastore_active_is_updated_if_true_and_provided():
    resource = factories.Resource(url="http://example.com", datastore_active=True)

    res_returned = helpers.call_action(
        "resource_update",
        id=resource["id"],
        url="http://example.com",
        name="Test",
        datastore_active=False,
    )

    assert not res_returned["datastore_active"]


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_datastore_active_not_present_if_not_provided_and_not_datastore_plugin_enabled():
    assert not p.plugin_loaded("datastore")

    resource = factories.Resource(url="http://example.com")

    res_returned = helpers.call_action(
        "resource_update",
        id=resource["id"],
        url="http://example.com",
        name="Test",
    )

    assert "datastore_active" not in res_returned


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_resourceupdate_mimetype_by_url():
    """The mimetype is guessed from the url

    Real world usage would be externally linking the resource and
    the mimetype would be guessed, based on the url

    """
    resource = factories.Resource(url="http://localhost/data.csv", name="Test")

    res_update = helpers.call_action(
        "resource_update",
        id=resource["id"],
        url="http://localhost/data.json",
    )

    org_mimetype = resource.pop("mimetype")
    upd_mimetype = res_update.pop("mimetype")

    assert org_mimetype != upd_mimetype
    assert upd_mimetype == "application/json"


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_resourceupdate_mimetype_by_user():
    """
    The mimetype is supplied by the user

    Real world usage would be using the FileStore API or web UI form to create a resource
    and the user wanted to specify the mimetype themselves
    """
    resource = factories.Resource(url="http://localhost/data.csv", name="Test")

    res_update = helpers.call_action(
        "resource_update",
        id=resource["id"],
        url="http://localhost/data.csv",
        mimetype="text/plain",
    )

    org_mimetype = resource.pop("mimetype")
    upd_mimetype = res_update.pop("mimetype")

    assert org_mimetype != upd_mimetype
    assert upd_mimetype == "text/plain"


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
@pytest.mark.ckan_config("ckan.mimetype_guess", "file_contents")
def test_resourceupdate_mimetype_by_upload_by_file(create_with_upload):
    """The mimetype is guessed from an uploaded file by the contents inside

    Real world usage would be using the FileStore API or web UI
    form to upload a file, that has no extension If the mimetype
    can't be guessed by the url or filename, mimetype will be
    guessed by the contents inside the file

    """
    resource = factories.Resource(url="http://localhost/data.csv", name="Test")

    content = """
    Snow Course Name, Number, Elev. metres, Date of Survey, Snow Depth cm, Water Equiv. mm, Survey Code, % of Normal, Density %, Survey Period, Normal mm
    SKINS LAKE,1B05,890,2015/12/30,34,53,,98,16,JAN-01,54
    MCGILLIVRAY PASS,1C05,1725,2015/12/31,88,239,,87,27,JAN-01,274
    NAZKO,1C08,1070,2016/01/05,20,31,,76,16,JAN-01,41
    """

    res_update = create_with_upload(
        content,
        "update_test",
        action="resource_update",
        id=resource["id"],
        url="http://localhost",
        package_id=resource["package_id"],
    )

    org_mimetype = resource.pop("mimetype")
    upd_mimetype = res_update.pop("mimetype")

    assert org_mimetype != upd_mimetype
    assert upd_mimetype == "text/plain"


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_resourceupdate_mimetype_by_upload_by_filename(create_with_upload):
    """The mimetype is guessed from an uploaded file with a filename

    Real world usage would be using the FileStore API or web UI
    form to upload a file, with a filename plus extension If
    there's no url or the mimetype can't be guessed by the url,
    mimetype will be guessed by the extension in the filename

    """
    content = """
    "info": {
        "title": "BC Data Catalogue API",
        "description": "This API provides information about datasets in the BC Data Catalogue.",
        "termsOfService": "http://www.data.gov.bc.ca/local/dbc/docs/license/API_Terms_of_Use.pdf",
        "contact": {
            "name": "Data BC",
            "url": "http://data.gov.bc.ca/",
            "email": ""
        },
        "license": {
            "name": "Open Government License - British Columbia",
            "url": "http://www.data.gov.bc.ca/local/dbc/docs/license/OGL-vbc2.0.pdf"
        },
        "version": "3.0.0"
    }
    """
    dataset = factories.Dataset()
    resource = create_with_upload(
        content,
        "test.json",
        package_id=dataset["id"],
        url="http://localhost",
    )

    content = """
    Snow Course Name, Number, Elev. metres, Date of Survey, Snow Depth cm, Water Equiv. mm, Survey Code, % of Normal, Density %, Survey Period, Normal mm
    SKINS LAKE,1B05,890,2015/12/30,34,53,,98,16,JAN-01,54
    MCGILLIVRAY PASS,1C05,1725,2015/12/31,88,239,,87,27,JAN-01,274
    NAZKO,1C08,1070,2016/01/05,20,31,,76,16,JAN-01,41
    """

    res_update = create_with_upload(
        content,
        "update_test.csv",
        action="resource_update",
        id=resource["id"],
        url="http://localhost",
        package_id=dataset["id"],
    )

    org_mimetype = resource.pop("mimetype")
    upd_mimetype = res_update.pop("mimetype")

    assert org_mimetype != upd_mimetype
    assert upd_mimetype == "text/csv"


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_resourceupdate_size_of_resource_by_user():
    """
    The size of the resource is provided by the users

    Real world usage would be using the FileStore API and the user provides a size for the resource
    """
    resource = factories.Resource(
        url="http://localhost/data.csv",
        name="Test",
        size=500,
    )

    res_update = helpers.call_action(
        "resource_update",
        id=resource["id"],
        url="http://localhost/data.csv",
        size=600,
    )

    org_size = int(resource.pop("size"))
    upd_size = int(res_update.pop("size"))

    assert org_size < upd_size


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_resourceupdate_size_of_resource_by_upload(create_with_upload):
    """The size of the resource determined by the uploaded file"""
    content = """
    "info": {
        "title": "BC Data Catalogue API",
        "description": "This API provides information about datasets in the BC Data Catalogue.",
        "termsOfService": "http://www.data.gov.bc.ca/local/dbc/docs/license/API_Terms_of_Use.pdf",
        "contact": {
            "name": "Data BC",
            "url": "http://data.gov.bc.ca/",
            "email": ""
        },
        "license": {
            "name": "Open Government License - British Columbia",
            "url": "http://www.data.gov.bc.ca/local/dbc/docs/license/OGL-vbc2.0.pdf"
        },
        "version": "3.0.0"
    }
    """

    dataset = factories.Dataset()

    resource = create_with_upload(
        content,
        "test.json",
        package_id=dataset["id"],
        url="http://localhost",
    )

    content = """
    Snow Course Name, Number, Elev. metres, Date of Survey, Snow Depth cm, Water Equiv. mm, Survey Code, % of Normal, Density %, Survey Period, Normal mm
    SKINS LAKE,1B05,890,2015/12/30,34,53,,98,16,JAN-01,54
    MCGILLIVRAY PASS,1C05,1725,2015/12/31,88,239,,87,27,JAN-01,274
    NAZKO,1C08,1070,2016/01/05,20,31,,76,16,JAN-01,41
    """
    res_update = create_with_upload(
        content,
        "update_test.csv",
        action="resource_update",
        id=resource["id"],
        url="http://localhost",
        package_id=dataset["id"],
    )

    org_size = int(resource.pop("size"))  # 669 bytes
    upd_size = int(res_update.pop("size"))  # 358 bytes

    assert org_size > upd_size


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_resource_uploads_after_reorder(create_with_upload):
    """
    Having different resource positions in the database
    should still allow for proper Resource uploads when
    updating a resource/package.

    Specifically tests the resources_all backref's order_by=position

    NOTE: this flaky error is based on db object return of resources
          in the package orm object. So we close and open db sessions
          inside of this test to emulate browser request sessions.
          Because of the flakiness, we update every resource w/ upload
          in a new db session.
    """
    content_1 = b"This is some raw text content..."
    content_2 = b"This is some COMPLETELY DIFFERENT raw text content..."

    dataset = factories.Dataset()
    original_order = []

    # create a bunch of resources, check uploaded content
    for i in range(0, 6):
        model.Session.commit()
        model.Session.remove()
        _session = model.Session  # noqa: F841
        resource = create_with_upload(
            content_1,
            "test_1.txt",
            package_id=dataset["id"],
            url="http://localhost",
        )
        original_order.append(resource["id"])
        assert resource["position"] == i
        assert (
            re.match(
                rf".*/dataset/{dataset['id']}/resource/{resource['id']}/download/test_1.txt$",
                resource["url"],
            )
            is not None
        )
        upload = uploader.get_resource_uploader(resource)

        filepath = upload.get_path(resource["id"])
        content = upload.storage.content(files.FileData(filepath))  # pyright: ignore[reportAttributeAccessIssue]
        assert content == content_1
        assert content != content_2

    dataset = model.Package.get(dataset["id"])
    for i, r in enumerate(dataset.resources):
        assert r.position == i

    # rearrange them
    assert len(original_order) == 6
    new_order = [
        original_order[4],
        original_order[5],
        original_order[0],
        original_order[2],
        original_order[3],
        original_order[1],
    ]
    helpers.call_action("package_resource_reorder", id=dataset.id, order=new_order)

    dataset = model.Package.get(dataset.id)
    for i, r in enumerate(dataset.resources):
        assert r.position == i

    # update all resources with new file, check content
    for rid in original_order:
        model.Session.commit()
        model.Session.remove()
        _session = model.Session  # noqa: F841
        resource = create_with_upload(
            content_2,
            "test_2.txt",
            package_id=dataset.id,
            action="resource_update",
            id=rid,
            url="http://localhost",
        )
        assert (
            re.match(
                rf".*/dataset/{dataset.id}/resource/{resource['id']}/download/test_2.txt$",
                resource["url"],
            )
            is not None
        )
        upload = uploader.get_resource_uploader(resource)
        filepath = upload.get_path(resource["id"])
        content = upload.storage.content(files.FileData(filepath))  # pyright: ignore[reportAttributeAccessIssue]
        assert content != content_1
        assert content == content_2

    # make a new resource after the reorder, check content
    model.Session.commit()
    model.Session.remove()
    _session = model.Session  # noqa: F841
    resource = create_with_upload(
        content_1,
        "test_1.txt",
        package_id=dataset.id,
        url="http://localhost",
    )
    assert (
        re.match(
            rf".*/dataset/{dataset.id}/resource/{resource['id']}/download/test_1.txt$",
            resource["url"],
        )
        is not None
    )
    upload = uploader.get_resource_uploader(resource)
    filepath = upload.get_path(resource["id"])
    content = upload.storage.content(files.FileData(filepath))  # pyright: ignore[reportAttributeAccessIssue]
    assert content == content_1
    assert content != content_2

    # update the new resource, check content
    model.Session.commit()
    model.Session.remove()
    _session = model.Session  # noqa: F841
    resource = create_with_upload(
        content_2,
        "test_2.txt",
        package_id=dataset.id,
        action="resource_update",
        id=resource["id"],
        url="http://localhost",
    )
    assert (
        re.match(
            rf".*/dataset/{dataset.id}/resource/{resource['id']}/download/test_2.txt$",
            resource["url"],
        )
        is not None
    )
    upload = uploader.get_resource_uploader(resource)
    filepath = upload.get_path(resource["id"])
    content = upload.storage.content(files.FileData(filepath))  # pyright: ignore[reportAttributeAccessIssue]
    assert content != content_1
    assert content == content_2

    helpers.call_action("package_delete", id=dataset.id)


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_resourceupdate_extras():
    user = factories.User()
    dataset = factories.Dataset(
        user=user,
        resources=[dict(format="json", url="http://datahub.io/")],
    )

    resource = helpers.call_action(
        "resource_update",
        id=dataset["resources"][0]["id"],
        somekey="somevalue",  # this is how to do resource extras
        extras={"someotherkey": "alt234"},  # this isn't
        format="plain text",
        url="http://datahub.io/download/",
    )

    assert resource["somekey"] == "somevalue"
    assert "extras" not in resource
    assert "someotherkey" not in resource
    resource = helpers.call_action("package_show", id=dataset["id"])["resources"][0]
    assert resource["somekey"] == "somevalue"
    assert "extras" not in resource
    assert "someotherkey" not in resource


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
@pytest.mark.ckan_config("ckan.views.default_views", "image_view text_view")
def test_resource_format_update():
    # Create resource without format
    resource = factories.Resource(url="http://localhost", name="Test", format="")
    res_views = helpers.call_action("resource_view_list", id=resource["id"])

    assert len(res_views) == 0

    # Update resource with format
    resource = helpers.call_action("resource_update", id=resource["id"], format="TXT")

    # Format changed
    assert resource["format"] == "TXT"

    res_views = helpers.call_action("resource_view_list", id=resource["id"])

    # View for resource is created
    assert len(res_views) == 1

    second_resource = factories.Resource(
        url="http://localhost", name="Test2", format="TXT"
    )

    res_views = helpers.call_action("resource_view_list", id=second_resource["id"])

    assert len(res_views) == 1

    second_resource = helpers.call_action(
        "resource_update", id=second_resource["id"], format="PNG"
    )

    # Format changed
    assert second_resource["format"] == "PNG"

    res_views = helpers.call_action("resource_view_list", id=second_resource["id"])

    assert len(res_views) == 2

    third_resource = factories.Resource(url="http://localhost", name="Test3", format="")

    res_views = helpers.call_action("resource_view_list", id=third_resource["id"])

    assert len(res_views) == 0

    third_resource = helpers.call_action(
        "resource_update", id=third_resource["id"], format="Test format"
    )

    # Format added
    assert third_resource["format"] == "Test format"

    res_views = helpers.call_action("resource_view_list", id=third_resource["id"])

    # No view created, cause no such format
    assert len(res_views) == 0

    third_resource = helpers.call_action(
        "resource_update", id=third_resource["id"], format="TXT"
    )

    # Format changed
    assert third_resource["format"] == "TXT"

    res_views = helpers.call_action("resource_view_list", id=third_resource["id"])

    # View is created
    assert len(res_views) == 1


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_edit_metadata_updates_metadata_modified_field():
    resource = factories.Resource()

    with freeze_time("2020-02-25 12:00:00"):
        resource = helpers.call_action(
            "resource_update",
            id=resource["id"],
            description="New Description",
        )
        assert resource["metadata_modified"] == "2020-02-25T12:00:00"
    package = helpers.call_action("package_show", id=resource["package_id"])
    assert package["metadata_modified"] == "2020-02-25T12:00:00"


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_same_values_dont_update_metadata_modified_field():
    with freeze_time("1987-03-04 23:30:00"):
        resource = factories.Resource(
            description="Test",
            some_custom_field="test",
            url="http://link.to.some.data",
        )
        assert resource["metadata_modified"] == datetime.datetime.utcnow().isoformat()
        package = helpers.call_action("package_show", id=resource["package_id"])
        assert package["metadata_modified"] == datetime.datetime.utcnow().isoformat()

    with freeze_time("2020-02-25 12:00:00"):
        resource = helpers.call_action(
            "resource_update",
            id=resource["id"],
            description="Test",
            some_custom_field="test",
            url="http://link.to.some.data",
        )
        assert resource["metadata_modified"] != datetime.datetime.utcnow().isoformat()
        assert resource["metadata_modified"] == "1987-03-04T23:30:00"
    package = helpers.call_action("package_show", id=resource["package_id"])
    assert package["metadata_modified"] == "1987-03-04T23:30:00"


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_new_keys_update_metadata_modified_field():
    with freeze_time("1987-03-04 23:30:00"):
        resource = factories.Resource(description="test")
        assert resource["metadata_modified"] == datetime.datetime.utcnow().isoformat()
        package = helpers.call_action("package_show", id=resource["package_id"])
        assert package["metadata_modified"] == datetime.datetime.utcnow().isoformat()

    with freeze_time("2020-02-25 12:00:00"):
        resource = helpers.call_action(
            "resource_update",
            id=resource["id"],
            description="test",
            some_custom_field="test",
            url="http://link.to.some.data",
        )
        now = datetime.datetime.utcnow().isoformat()
        assert resource["metadata_modified"] == now
        package = helpers.call_action("package_show", id=resource["package_id"])
        assert package["metadata_modified"] == now


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_remove_keys_update_metadata_modified_field():
    with freeze_time("1987-03-04 23:30:00"):
        resource = factories.Resource(
            description="test",
            some_custom_field="test",
        )
        assert resource["metadata_modified"] == datetime.datetime.utcnow().isoformat()
        package = helpers.call_action("package_show", id=resource["package_id"])
        assert package["metadata_modified"] == datetime.datetime.utcnow().isoformat()

    with freeze_time("2020-02-25 12:00:00"):
        resource = helpers.call_action(
            "resource_update",
            id=resource["id"],
            description="test",
            url="http://link.to.some.data",  # default value from factory
        )
        now = datetime.datetime.utcnow().isoformat()
        assert resource["metadata_modified"] == now
        package = helpers.call_action("package_show", id=resource["package_id"])
        assert package["metadata_modified"] == now


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_update_keys_update_metadata_modified_field():
    with freeze_time("1987-03-04 23:30:00"):
        resource = factories.Resource(
            description="test",
            some_custom_field="test",
        )
        assert resource["metadata_modified"] == datetime.datetime.utcnow().isoformat()
        package = helpers.call_action("package_show", id=resource["package_id"])
        assert package["metadata_modified"] == datetime.datetime.utcnow().isoformat()

    with freeze_time("2020-02-25 12:00:00"):
        resource = helpers.call_action(
            "resource_update",
            id=resource["id"],
            description="test",
            some_custom_field="test2",
            url="http://link.to.some.data",  # default value from factory
        )
        now = datetime.datetime.utcnow().isoformat()
        assert resource["metadata_modified"] == now
        package = helpers.call_action("package_show", id=resource["package_id"])
        assert package["metadata_modified"] == now


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_resource_update_for_update():
    resource = factories.Resource()

    mock_package_show = mock.MagicMock()
    mock_package_show.side_effect = lambda context, data_dict: core_package_show(
        context, data_dict
    )

    with mock.patch.dict("ckan.logic._actions", {"package_show": mock_package_show}):
        helpers.call_action("resource_update", id=resource["id"], description="hey")
        assert mock_package_show.call_args_list[0][0][0].get("for_update") is True


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_resource_reorder_for_update():

    dataset = factories.Dataset()
    resource1 = factories.Resource(package_id=dataset["id"])
    resource2 = factories.Resource(package_id=dataset["id"])

    mock_package_show = mock.MagicMock()
    mock_package_show.side_effect = lambda context, data_dict: core_package_show(
        context, data_dict
    )

    with mock.patch.dict("ckan.logic._actions", {"package_show": mock_package_show}):
        helpers.call_action(
            "package_resource_reorder",
            id=dataset["id"],
            order=[resource2["id"], resource1["id"]],
        )
        assert mock_package_show.call_args_list[0][0][0].get("for_update") is True


@pytest.mark.ckan_config("ckan.plugins", "image_view text_view resource_proxy")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_resource_update_copies_other_resources():
    from ckan.lib.dictization import model_save

    res1 = factories.Resource()
    res2 = factories.Resource(package_id=res1["package_id"], url="http://data")
    factories.Resource(package_id=res1["package_id"])
    params = {
        "id": res2["id"],
        "url": "http://data2",
    }
    with mock.patch(
        "ckan.lib.dictization.model_save.package_dict_save",
        wraps=model_save.package_dict_save,
    ) as m:
        helpers.call_action("resource_update", **params)
        assert m.call_args.args[3] == {0: 0, 2: 2}, "unchanged res 0, 2"
