"""Tests for actions and authorization in ckan/logic/action/package.py."""

import unittest.mock as mock
import uuid
import pytest
import sqlalchemy as sa
import ckan.logic as logic
import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import re

from freezegun import freeze_time

from ckan.logic.action.package import package_show as core_package_show
from ckan.lib.search.common import SearchError
from ckan.logic import ValidationError


@pytest.mark.usefixtures("non_clean_db")
def test_private_package():
    org = factories.Organization()
    stub = factories.Dataset.stub()
    with pytest.raises(logic.ValidationError):
        pkg = helpers.call_action("package_create", name=stub.name, private=True)

    pkg = helpers.call_action("package_create", owner_org=org["id"], name=stub.name)
    assert not pkg["private"]
    pkg = helpers.call_action(
        "package_create",
        owner_org=org["id"],
        name=factories.Dataset.stub().name,
        private=False,
    )
    assert not pkg["private"]
    pkg = helpers.call_action(
        "package_create",
        owner_org=org["id"],
        name=factories.Dataset.stub().name,
        private=True,
    )
    assert pkg["private"]


@pytest.mark.usefixtures("non_clean_db")
def test_normal_user_cant_set_id():
    user = factories.User()
    context = {"user": user["name"], "ignore_auth": False}
    _id = str(uuid.uuid4())
    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "package_create",
            context=context,
            id=_id,
            name="test",
        )


@pytest.mark.usefixtures("non_clean_db")
def test_sysadmin_can_set_id():
    user = factories.Sysadmin()
    context = {"user": user["name"], "ignore_auth": False}
    _id = str(uuid.uuid4())
    dataset = helpers.call_action(
        "package_create", context=context, id=_id, name=f"test-dataset-{_id}"
    )
    assert dataset["id"] == _id


@pytest.mark.usefixtures("non_clean_db")
def test_context_is_not_polluted():
    user = factories.Sysadmin()
    context = {"user": user["name"], "ignore_auth": False}
    _id = str(uuid.uuid4())
    helpers.call_action(
        "package_create", context=context, id=_id, name=f"test-dataset-{_id}"
    )
    assert "id" not in context
    assert "package" not in context


@pytest.mark.usefixtures("non_clean_db")
def test_id_cant_already_exist():
    dataset = factories.Dataset()
    factories.Sysadmin()
    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "package_create",
            id=dataset["id"],
            name=factories.Dataset.stub().name,
        )


@pytest.mark.usefixtures("non_clean_db")
def test_name_not_changed_during_deletion():
    dataset = factories.Dataset()
    helpers.call_action("package_delete", id=dataset["id"])
    deleted_dataset = helpers.call_action("package_show", id=dataset["id"])
    assert deleted_dataset["name"] == dataset["name"]


@pytest.mark.usefixtures("non_clean_db")
def test_name_not_changed_after_restoring():
    dataset = factories.Dataset()
    context = {"user": factories.Sysadmin()["name"]}
    helpers.call_action("package_delete", id=dataset["id"])
    deleted_dataset = helpers.call_action("package_show", id=dataset["id"])
    restored_dataset = helpers.call_action(
        "package_patch", context=context, id=dataset["id"], state="active"
    )
    assert deleted_dataset["name"] == restored_dataset["name"]
    assert deleted_dataset["id"] == restored_dataset["id"]


@pytest.mark.usefixtures("non_clean_db")
def test_creation_of_dataset_with_name_same_as_of_previously_removed():
    dataset = factories.Dataset()
    initial_name = dataset["name"]
    helpers.call_action("package_delete", id=dataset["id"])
    new_dataset = helpers.call_action("package_create", name=initial_name)
    assert new_dataset["name"] == initial_name
    deleted_dataset = helpers.call_action("package_show", id=dataset["id"])

    assert new_dataset["id"] != deleted_dataset["id"]
    assert deleted_dataset["name"] == deleted_dataset["id"]


@pytest.mark.usefixtures("non_clean_db")
def test_missing_id():
    with pytest.raises(logic.ValidationError):
        helpers.call_action("package_create")


@pytest.mark.usefixtures("non_clean_db")
def test_name():
    stub = factories.Dataset.stub()
    dataset = helpers.call_action("package_create", name=stub.name)

    assert dataset["name"] == stub.name
    assert helpers.call_action("package_show", id=dataset["id"])["name"] == stub.name


@pytest.mark.usefixtures("non_clean_db")
def test_title():
    dataset = helpers.call_action(
        "package_create",
        name=factories.Dataset.stub().name,
        title="New Title",
    )

    assert dataset["title"] == "New Title"
    assert helpers.call_action("package_show", id=dataset["id"])["title"] == "New Title"


@pytest.mark.usefixtures("non_clean_db")
def test_extras():
    dataset = helpers.call_action(
        "package_create",
        name=factories.Dataset.stub().name,
        title="Test Extras",
        extras=[{"key": "original media", "value": '"book"'}],
    )

    assert dataset["extras"][0]["key"] == "original media"
    assert dataset["extras"][0]["value"] == '"book"'
    dataset = helpers.call_action("package_show", id=dataset["id"])
    assert dataset["extras"][0]["key"] == "original media"
    assert dataset["extras"][0]["value"] == '"book"'


@pytest.mark.usefixtures("non_clean_db")
def test_sysadmin_can_set_extras_id():
    user = factories.Sysadmin()
    context = {"user": user["name"], "ignore_auth": False}
    _id = str(uuid.uuid4())
    dataset = helpers.call_action(
        "package_create",
        context=context,
        name=factories.Dataset.stub().name,
        title="Test Extras",
        extras=[{"id": _id, "key": "original media", "value": '"book"'}],
    )
    dataset = helpers.call_action("package_show", id=dataset["id"])
    assert dataset["extras"][0]["key"] == "original media"


@pytest.mark.usefixtures("non_clean_db")
def test_normal_user_can_not_set_extras_id():
    user = factories.User()
    context = {"user": user["name"], "ignore_auth": False}
    _id = str(uuid.uuid4())
    with pytest.raises(logic.ValidationError) as exception:
        helpers.call_action(
            "package_create",
            context=context,
            name=factories.Dataset.stub().name,
            title="Test Extras",
            extras=[{"id": _id, "key": "original media", "value": '"book"'}],
        )
    assert "The input field id was not expected" in str(exception.value)


@pytest.mark.usefixtures("non_clean_db")
def test_license():
    dataset = helpers.call_action(
        "package_create",
        name=factories.Dataset.stub().name,
        title="Test License",
        license_id="other-open",
    )

    assert dataset["license_id"] == "other-open"
    dataset = helpers.call_action("package_show", id=dataset["id"])
    assert dataset["license_id"] == "other-open"


@pytest.mark.usefixtures("non_clean_db")
def test_notes():
    dataset = helpers.call_action(
        "package_create",
        name=factories.Dataset.stub().name,
        title="Test Notes",
        notes="some notes",
    )

    assert dataset["notes"] == "some notes"
    dataset = helpers.call_action("package_show", id=dataset["id"])
    assert dataset["notes"] == "some notes"


@pytest.mark.usefixtures("non_clean_db")
def test_resources():
    dataset = helpers.call_action(
        "package_create",
        name=factories.Dataset.stub().name,
        title="Test Resources",
        resources=[
            {
                "alt_url": "alt123",
                "description": "Full text.",
                "somekey": "somevalue",  # this is how to do resource extras
                "extras": {"someotherkey": "alt234"},  # this isn't
                "format": "plain text",
                "hash": "abc123",
                "position": 0,
                "url": "http://datahub.io/download/",
            },
            {
                "description": "Index of the novel",
                "format": "JSON",
                "position": 1,
                "url": "http://datahub.io/index.json",
            },
        ],
    )

    resources = dataset["resources"]
    assert resources[0]["alt_url"] == "alt123"
    assert resources[0]["description"] == "Full text."
    assert resources[0]["somekey"] == "somevalue"
    assert "extras" not in resources[0]
    assert "someotherkey" not in resources[0]
    assert resources[0]["format"] == "plain text"
    assert resources[0]["hash"] == "abc123"
    assert resources[0]["position"] == 0
    assert resources[0]["url"] == "http://datahub.io/download/"
    assert resources[1]["description"] == "Index of the novel"
    assert resources[1]["format"] == "JSON"
    assert resources[1]["url"] == "http://datahub.io/index.json"
    assert resources[1]["position"] == 1
    resources = helpers.call_action("package_show", id=dataset["id"])["resources"]
    assert resources[0]["alt_url"] == "alt123"
    assert resources[0]["description"] == "Full text."
    assert resources[0]["somekey"] == "somevalue"
    assert "extras" not in resources[0]
    assert "someotherkey" not in resources[0]
    assert resources[0]["format"] == "plain text"
    assert resources[0]["hash"] == "abc123"
    assert resources[0]["position"] == 0
    assert resources[0]["url"] == "http://datahub.io/download/"
    assert resources[1]["description"] == "Index of the novel"
    assert resources[1]["format"] == "JSON"
    assert resources[1]["url"] == "http://datahub.io/index.json"
    assert resources[1]["position"] == 1


@pytest.mark.usefixtures("non_clean_db")
def test_tags():
    tag1 = factories.Tag.stub().name
    tag2 = factories.Tag.stub().name
    dataset = helpers.call_action(
        "package_create",
        name=factories.Dataset.stub().name,
        title="Test Tags",
        tags=[{"name": tag1}, {"name": tag2}],
    )

    tag_names = sorted([tag_dict["name"] for tag_dict in dataset["tags"]])
    assert tag_names == sorted([tag1, tag2])
    dataset = helpers.call_action("package_show", id=dataset["id"])
    tag_names = sorted([tag_dict["name"] for tag_dict in dataset["tags"]])
    assert tag_names == sorted([tag1, tag2])


@pytest.mark.usefixtures("non_clean_db")
def test_return_id_only():
    dataset = helpers.call_action(
        "package_create",
        name=factories.Dataset.stub().name,
        context={"return_id_only": True},
    )

    assert isinstance(dataset, str)


@pytest.mark.usefixtures("non_clean_db")
def test_non_string_extras():
    data_dict = {
        "name": "test-non-string-extras",
        "extras": [{"key": "some_number", "value": 1.5}],
    }

    helpers.call_action("package_create", **data_dict)


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", False)
def test_create_package_collaborator_when_config_disabled():

    dataset = factories.Dataset()
    user = factories.User()
    capacity = "editor"

    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity=capacity,
        )


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_create():
    initial = model.Session.query(model.PackageMember).count()
    dataset = factories.Dataset()
    user = factories.User()
    capacity = "editor"

    member = helpers.call_action(
        "package_collaborator_create",
        id=dataset["id"],
        user_id=user["id"],
        capacity=capacity,
    )

    assert member["package_id"] == dataset["id"]
    assert member["user_id"] == user["id"]
    assert member["capacity"] == capacity

    assert model.Session.query(model.PackageMember).count() == initial + 1


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_update():
    dataset = factories.Dataset()
    user = factories.User()
    capacity = "editor"

    helpers.call_action(
        "package_collaborator_create",
        id=dataset["id"],
        user_id=user["id"],
        capacity=capacity,
    )

    helpers.call_action(
        "package_collaborator_create",
        id=dataset["id"],
        user_id=user["id"],
        capacity="member",
    )

    assert (
        model.Session.query(model.PackageMember)
        .filter_by(package_id=dataset["id"])
        .one()
        .capacity
        == "member"
    )


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_create_wrong_capacity():
    dataset = factories.Dataset()
    user = factories.User()
    capacity = "unknown"

    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity=capacity,
        )


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_create_dataset_not_found():
    dataset = {"id": "xxx"}
    user = factories.User()
    capacity = "editor"

    with pytest.raises(logic.NotFound):
        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity=capacity,
        )


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_create_user_not_found():
    dataset = factories.Dataset()
    user = {"id": "yyy"}
    capacity = "editor"

    with pytest.raises(logic.NotFound):
        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity=capacity,
        )


@pytest.mark.usefixtures("clean_db")
def test_stored_on_create_if_sysadmin():
    sysadmin = factories.Sysadmin()

    pkg_dict = {"name": "test-dataset", "plugin_data": {"plugin1": {"key1": "value1"}}}
    context = {
        "user": sysadmin["name"],
        "ignore_auth": False,
        "auth_user_obj": model.User.get(sysadmin["name"]),
    }
    created_pkg = helpers.call_action("package_create", context=context, **pkg_dict)
    plugin_data_from_db = model.Session.execute(
        sa.text('SELECT plugin_data FROM "package" WHERE id=:id'),
        {"id": created_pkg["id"]},
    ).first()[0]

    assert plugin_data_from_db == {"plugin1": {"key1": "value1"}}


@pytest.mark.usefixtures("clean_db")
def test_ignored_on_create_if_non_sysadmin():
    user = factories.User()

    pkg_dict = {"name": "test-dataset", "plugin_data": {"plugin1": {"key1": "value1"}}}
    context = {
        "user": user["name"],
        "ignore_auth": False,
    }
    created_pkg = helpers.call_action("package_create", context=context, **pkg_dict)
    assert "plugin_data" not in created_pkg

    plugin_data_from_db = model.Session.execute(
        sa.text('SELECT plugin_data FROM "package" WHERE id=:id'),
        {"id": created_pkg["id"]},
    ).first()[0]
    assert plugin_data_from_db is None


@pytest.mark.usefixtures("non_clean_db")
def test_a_non_sysadmin_cant_purge_dataset():
    user = factories.User()
    dataset = factories.Dataset(user=user)

    with pytest.raises(logic.NotAuthorized):
        helpers.call_action(
            "dataset_purge",
            context={"user": user["name"], "ignore_auth": False},
            id=dataset["name"],
        )


@pytest.mark.usefixtures("non_clean_db")
def test_purged_dataset_does_not_show():
    dataset = factories.Dataset()

    helpers.call_action(
        "dataset_purge", context={"ignore_auth": True}, id=dataset["name"]
    )

    with pytest.raises(logic.NotFound):
        helpers.call_action("package_show", context={}, id=dataset["name"])


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.usefixtures("clean_db")
def test_purged_dataset_is_not_listed():
    dataset = factories.Dataset()

    helpers.call_action("dataset_purge", id=dataset["name"])

    assert helpers.call_action("package_list", context={}) == []


@pytest.mark.usefixtures("non_clean_db")
def test_group_no_longer_shows_its_purged_dataset():
    group = factories.Group()
    dataset = factories.Dataset(groups=[{"name": group["name"]}])

    helpers.call_action("dataset_purge", id=dataset["name"])

    dataset_shown = helpers.call_action(
        "group_show", context={}, id=group["id"], include_datasets=True
    )
    assert dataset_shown["packages"] == []


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.usefixtures("clean_index", "with_plugins")
def test_purged_dataset_is_not_in_search_results():
    dataset = factories.Dataset()

    def get_search_results():
        results = helpers.call_action("package_search", q=dataset["title"])["results"]
        return [d["name"] for d in results]

    assert get_search_results() == [dataset["name"]]
    helpers.call_action("dataset_purge", id=dataset["name"])

    assert get_search_results() == []


@pytest.mark.usefixtures("non_clean_db")
def test_purged_dataset_leaves_no_trace_in_the_model():
    group = factories.Group()
    org = factories.Organization()
    tag = factories.Tag.stub().name
    dataset = factories.Dataset(
        tags=[{"name": tag}],
        groups=[{"name": group["name"]}],
        owner_org=org["id"],
        extras=[{"key": "testkey", "value": "testvalue"}],
    )
    factories.Resource(package_id=dataset["id"])

    helpers.call_action(
        "dataset_purge", context={"ignore_auth": True}, id=dataset["name"]
    )

    # the Package and related objects are gone
    assert not model.Package.get(dataset["id"])
    assert (
        model.Session.query(model.Resource).filter_by(package_id=dataset["id"]).all()
        == []
    )
    assert (
        model.Session.query(model.PackageTag).filter_by(package_id=dataset["id"]).all()
        == []
    )
    # there is no clean-up of the tag object itself, just the PackageTag.
    assert model.Session.query(model.Tag).filter_by(name=tag).one()

    # the only member left is for the user created in factories.Group() and
    # factories.Organization()
    assert sorted(
        (m.table_name, m.group.name)
        for m in model.Session.query(model.Member)
        .join(model.Group)
        .filter(model.Group.id.in_([group["id"], org["id"]]))
    ) == sorted([("user", group["name"]), ("user", org["name"])])


@pytest.mark.usefixtures("non_clean_db")
def test_purged_dataset_removed_from_relationships():
    child = factories.Dataset()
    parent = factories.Dataset()
    grandparent = factories.Dataset()

    helpers.call_action(
        "package_relationship_create",
        subject=child["id"],
        type="child_of",
        object=parent["id"],
    )

    helpers.call_action(
        "package_relationship_create",
        subject=parent["id"],
        type="child_of",
        object=grandparent["id"],
    )

    assert len(model.Session.query(model.PackageRelationship).all()) == 2

    helpers.call_action(
        "dataset_purge", context={"ignore_auth": True}, id=parent["name"]
    )

    assert model.Session.query(model.PackageRelationship).all() == []


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_purged_dataset_with_collaborators():
    dataset = factories.Dataset()
    user = factories.User()
    helpers.call_action(
        "package_collaborator_create",
        id=dataset["id"],
        user_id=user["id"],
        capacity="editor",
    )

    helpers.call_action("dataset_purge", id=dataset["id"])

    assert not model.Package.get(dataset["id"])
    assert (
        model.Session.query(model.PackageMember)
        .filter_by(package_id=dataset["id"])
        .all()
        == []
    )


@pytest.mark.usefixtures("non_clean_db")
def test_missing_id_returns_error():
    with pytest.raises(logic.ValidationError):
        helpers.call_action("dataset_purge")


@pytest.mark.usefixtures("non_clean_db")
def test_bad_id_returns_404():
    with pytest.raises(logic.NotFound):
        helpers.call_action("dataset_purge", id="123")


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", False)
def test_delete_package_collaborator_when_config_disabled():

    dataset = factories.Dataset()
    user = factories.User()

    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "package_collaborator_delete", id=dataset["id"], user_id=user["id"]
        )


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_delete():

    dataset = factories.Dataset()
    user = factories.User()
    capacity = "editor"

    helpers.call_action(
        "package_collaborator_create",
        id=dataset["id"],
        user_id=user["id"],
        capacity=capacity,
    )

    assert (
        model.Session.query(model.PackageMember)
        .filter_by(package_id=dataset["id"])
        .count()
        == 1
    )

    helpers.call_action(
        "package_collaborator_delete", id=dataset["id"], user_id=user["id"]
    )

    assert (
        model.Session.query(model.PackageMember)
        .filter_by(package_id=dataset["id"])
        .count()
        == 0
    )


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_delete_dataset_not_found():
    dataset = {"id": "xxx"}
    user = factories.User()

    with pytest.raises(logic.NotFound):
        helpers.call_action(
            "package_collaborator_delete",
            id=dataset["id"],
            user_id=user["id"],
        )


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_delete_user_not_found():
    dataset = factories.Dataset()
    user = {"id": "yyy"}

    with pytest.raises(logic.NotFound):
        helpers.call_action(
            "package_collaborator_delete",
            id=dataset["id"],
            user_id=user["id"],
        )


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_package_delete_removes_collaborations():

    user = factories.User()
    dataset = factories.Dataset()
    helpers.call_action(
        "package_collaborator_create",
        id=dataset["id"],
        user_id=user["id"],
        capacity="editor",
    )

    assert (
        len(helpers.call_action("package_collaborator_list_for_user", id=user["id"]))
        == 1
    )

    context = {}
    params = {"id": dataset["id"]}

    helpers.call_action("package_delete", context, **params)

    assert (
        len(helpers.call_action("package_collaborator_list_for_user", id=user["id"]))
        == 0
    )


@pytest.mark.usefixtures("non_clean_db")
def test_package_show():
    # simple dataset, simple checks
    dataset1 = factories.Dataset()

    dataset2 = helpers.call_action("package_show", id=dataset1["id"])

    assert dataset2["name"] == dataset1["name"]
    missing_keys = set(("title", "groups")) - set(dataset2.keys())
    assert not missing_keys, missing_keys


@pytest.mark.usefixtures("non_clean_db")
def test_package_show_with_full_dataset():
    # an full dataset
    org = factories.Organization()
    group = factories.Group()
    dataset1 = factories.Dataset(
        resources=[
            {
                "url": "http://example.com/image.png",
                "format": "png",
                "name": "Image 1",
            }
        ],
        tags=[{"name": factories.Tag.stub().name}],
        extras=[{"key": "subject", "value": "science"}],
        groups=[{"id": group["id"]}],
        owner_org=org["id"],
    )
    dataset2 = helpers.call_action("package_show", id=dataset1["id"])

    # checking the whole dataset is a bit brittle as a test, but it
    # documents what the package_dict is clearly and tracks how it changes
    # as CKAN changes over time.

    # fix values which change every time you run this test
    def replace_uuid(dict_, key):
        assert key in dict_
        dict_[key] = "<SOME-UUID>"

    def replace_datetime(dict_, key):
        assert key in dict_
        dict_[key] = "2019-05-24T15:52:30.123456"

    def replace_number_suffix(dict_, key):
        # e.g. "Test Dataset 23" -> "Test Dataset "
        assert key in dict_
        dict_[key] = re.sub(r"\d+$", "num", dict_[key])

    replace_uuid(dataset2, "id")
    replace_uuid(dataset2, "creator_user_id")
    replace_uuid(dataset2, "owner_org")
    replace_number_suffix(dataset2, "name")
    replace_datetime(dataset2, "metadata_created")
    replace_datetime(dataset2, "metadata_modified")
    replace_datetime(dataset2["resources"][0], "metadata_modified")
    replace_uuid(dataset2["groups"][0], "id")
    replace_number_suffix(dataset2["groups"][0], "name")
    replace_number_suffix(dataset2["groups"][0], "title")
    replace_number_suffix(dataset2["groups"][0], "display_name")
    replace_uuid(dataset2["organization"], "id")
    replace_number_suffix(dataset2["organization"], "name")
    replace_number_suffix(dataset2["organization"], "title")
    replace_datetime(dataset2["organization"], "created")
    replace_uuid(dataset2["resources"][0], "id")
    replace_uuid(dataset2["resources"][0], "package_id")
    replace_number_suffix(dataset2["resources"][0], "name")
    replace_datetime(dataset2["resources"][0], "created")
    replace_uuid(dataset2["tags"][0], "id")

    assert dataset2 == {
        "author": dataset1["author"],
        "author_email": dataset1["author_email"],
        "creator_user_id": "<SOME-UUID>",
        "extras": dataset1["extras"],
        "groups": [
            {
                "description": group["description"],
                "display_name": group["display_name"],
                "id": "<SOME-UUID>",
                "image_display_url": group["image_display_url"],
                "name": group["name"],
                "title": group["title"],
            }
        ],
        "id": "<SOME-UUID>",
        "isopen": dataset1["isopen"],
        "license_id": dataset1["license_id"],
        "license_title": dataset1["license_title"],
        "maintainer": dataset1["maintainer"],
        "maintainer_email": dataset1["maintainer_email"],
        "metadata_created": "2019-05-24T15:52:30.123456",
        "metadata_modified": "2019-05-24T15:52:30.123456",
        "name": dataset1["name"],
        "notes": dataset1["notes"],
        "num_resources": dataset1["num_resources"],
        "num_tags": dataset1["num_tags"],
        "organization": {
            "approval_status": org["approval_status"],
            "created": "2019-05-24T15:52:30.123456",
            "description": org["description"],
            "id": "<SOME-UUID>",
            "image_url": org["image_url"],
            "is_organization": org["is_organization"],
            "name": org["name"],
            "state": org["state"],
            "title": org["title"],
            "type": org["type"],
        },
        "owner_org": "<SOME-UUID>",
        "private": dataset1["private"],
        "relationships_as_object": dataset1["relationships_as_object"],
        "relationships_as_subject": dataset1["relationships_as_subject"],
        "resources": [
            {
                "cache_last_updated": None,
                "cache_url": dataset1["resources"][0]["cache_url"],
                "created": "2019-05-24T15:52:30.123456",
                "description": dataset1["resources"][0]["description"],
                "format": dataset1["resources"][0]["format"],
                "hash": "",
                "id": "<SOME-UUID>",
                "last_modified": dataset1["resources"][0]["last_modified"],
                "metadata_modified": "2019-05-24T15:52:30.123456",
                "mimetype": dataset1["resources"][0]["mimetype"],
                "mimetype_inner": None,
                "name": "Image num",
                "package_id": "<SOME-UUID>",
                "position": dataset1["resources"][0]["position"],
                "resource_type": dataset1["resources"][0]["resource_type"],
                "size": dataset1["resources"][0]["size"],
                "state": dataset1["resources"][0]["state"],
                "url": dataset1["resources"][0]["url"],
                "url_type": dataset1["resources"][0]["url_type"],
            }
        ],
        "state": dataset1["state"],
        "tags": [
            {
                "display_name": dataset1["tags"][0]["display_name"],
                "id": "<SOME-UUID>",
                "name": dataset1["tags"][0]["name"],
                "state": dataset1["tags"][0]["state"],
                "vocabulary_id": dataset1["tags"][0]["vocabulary_id"],
            }
        ],
        "title": dataset1["title"],
        "type": dataset1["type"],
        "url": dataset1["url"],
        "version": dataset1["version"],
    }


@pytest.mark.usefixtures("non_clean_db")
def test_package_show_with_custom_schema():
    dataset1 = factories.Dataset()
    from ckan.logic.schema import default_show_package_schema

    custom_schema = default_show_package_schema()

    def foo(key, data, errors, context):  # noqa
        data[key] = "foo"

    custom_schema["new_field"] = [foo]

    dataset2 = helpers.call_action(
        "package_show",
        id=dataset1["id"],
        context={"schema": custom_schema},
    )

    assert dataset2["new_field"] == "foo"


@pytest.mark.usefixtures("non_clean_db")
def test_package_show_with_custom_schema_return_default_schema():
    dataset1 = factories.Dataset()
    from ckan.logic.schema import default_show_package_schema

    custom_schema = default_show_package_schema()

    def foo(key, data, errors, context):  # noqa
        data[key] = "foo"

    custom_schema["new_field"] = [foo]

    dataset2 = helpers.call_action(
        "package_show",
        id=dataset1["id"],
        use_default_schema=True,
        context={"schema": custom_schema},
    )

    assert "new_field" not in dataset2


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_current_package_list():
    """
    Test current_package_list_with_resources with no parameters
    """
    user = factories.User()
    factories.Dataset(user=user)
    factories.Dataset(user=user)
    current_package_list = helpers.call_action("current_package_list_with_resources")
    assert len(current_package_list) == 2


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_current_package_list_limit_param():
    """
    Test current_package_list_with_resources with limit parameter
    """
    user = factories.User()
    factories.Dataset(user=user)
    dataset2 = factories.Dataset(user=user)
    current_package_list = helpers.call_action(
        "current_package_list_with_resources", limit=1
    )
    assert len(current_package_list) == 1
    assert current_package_list[0]["name"] == dataset2["name"]


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_current_package_list_offset_param():
    """
    Test current_package_list_with_resources with offset parameter
    """
    user = factories.User()
    dataset1 = factories.Dataset(user=user)
    factories.Dataset(user=user)
    current_package_list = helpers.call_action(
        "current_package_list_with_resources", offset=1
    )
    assert len(current_package_list) == 1
    assert current_package_list[0]["name"] == dataset1["name"]


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_current_package_list_private_datasets_anonoymous_user():
    """
    Test current_package_list_with_resources with an anonymous user and
    a private dataset
    """
    user = factories.User()
    org = factories.Organization(user=user)
    factories.Dataset(user=user, owner_org=org["name"], private=True)
    factories.Dataset(user=user)
    current_package_list = helpers.call_action(
        "current_package_list_with_resources", context={}
    )
    assert len(current_package_list) == 1


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_current_package_list_private_datasets_sysadmin_user():
    """
    Test current_package_list_with_resources with a sysadmin user and a
    private dataset
    """
    user = factories.User()
    org = factories.Organization(user=user)
    factories.Dataset(user=user, owner_org=org["name"], private=True)
    factories.Dataset(user=user)
    sysadmin = factories.Sysadmin()
    current_package_list = helpers.call_action(
        "current_package_list_with_resources",
        context={"user": sysadmin["name"]},
    )
    assert len(current_package_list) == 2


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_package_autocomplete_match_name():
    pkg = factories.Dataset(name="warandpeace")
    result = helpers.call_action("package_autocomplete", q="war")
    assert result[0]["name"] == pkg["name"]
    assert result[0]["title"] == pkg["title"]
    assert result[0]["match_field"] == "name"
    assert result[0]["match_displayed"] == pkg["name"]


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_package_autocomplete_match_title():
    pkg = factories.Dataset(title="A Wonderful Story")
    result = helpers.call_action("package_autocomplete", q="won")
    assert result[0]["name"] == pkg["name"]
    assert result[0]["title"] == pkg["title"]
    assert result[0]["match_field"] == "title"
    assert result[0]["match_displayed"] == f"A Wonderful Story ({pkg['name']})"


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_package_autocomplete_does_not_return_private_datasets():

    user = factories.User()
    org = factories.Organization(user=user)
    factories.Dataset(user=user, owner_org=org["name"], title="Some public stuff")
    factories.Dataset(
        user=user,
        owner_org=org["name"],
        private=True,
        title="Some private stuff",
    )

    package_list = helpers.call_action(
        "package_autocomplete", context={"ignore_auth": False}, q="some"
    )
    assert len(package_list) == 1


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_package_autocomplete_does_return_private_datasets_from_my_org():
    user = factories.User()
    org = factories.Organization(users=[{"name": user["name"], "capacity": "member"}])
    factories.Dataset(user=user, owner_org=org["id"], title="Some public stuff")
    factories.Dataset(
        user=user,
        owner_org=org["id"],
        private=True,
        title="Some private stuff",
    )
    package_list = helpers.call_action(
        "package_autocomplete",
        context={"user": user["name"], "ignore_auth": False},
        q="some",
    )
    assert len(package_list) == 2


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_package_autocomplete_works_for_the_middle_part_of_title():
    factories.Dataset(title="Some public stuff")
    factories.Dataset(title="Some random stuff")

    package_list = helpers.call_action("package_autocomplete", q="bli")
    assert len(package_list) == 1
    package_list = helpers.call_action("package_autocomplete", q="tuf")
    assert len(package_list) == 2


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestPackageSearch(object):
    def test_search(self):
        factories.Dataset(title="Rivers")
        factories.Dataset(title="Lakes")  # decoy

        search_result = helpers.call_action("package_search", q="rivers")

        assert search_result["results"][0]["title"] == "Rivers"
        assert search_result["count"] == 1

    def test_search_fl(self):
        d1 = factories.Dataset(title="Rivers", name="test_ri")
        factories.Dataset(title="Lakes")

        search_result = helpers.call_action(
            "package_search", q="rivers", fl=["title", "name"]
        )
        assert search_result["results"] == [{"title": "Rivers", "name": "test_ri"}]

        search_result = helpers.call_action(
            "package_search", q="rivers", fl="title,name"
        )
        assert search_result["results"] == [{"title": "Rivers", "name": "test_ri"}]

        search_result = helpers.call_action("package_search", q="rivers", fl=["id"])
        assert search_result["results"] == [{"id": d1["id"]}]

    def test_search_all(self):
        factories.Dataset(title="Rivers")
        factories.Dataset(title="Lakes")

        search_result = helpers.call_action("package_search")  # no q

        assert search_result["count"] == 2

    def test_bad_action_parameter(self):
        with pytest.raises(SearchError):
            helpers.call_action("package_search", weird_param=1)

    def test_bad_solr_parameter(self):
        with pytest.raises(SearchError):
            helpers.call_action("package_search", sort="metadata_modified")
        # SOLR doesn't like that we didn't specify 'asc' or 'desc'
        # SOLR error is 'Missing sort order' or 'Missing_sort_order',
        # depending on the solr version.

    def _create_bulk_datasets(self, name, count):
        for i in range(count):
            factories.Dataset(name=f"{name}_{i}")

    def test_rows_returned_default(self):
        self._create_bulk_datasets("rows_default", 11)
        results = logic.get_action("package_search")({}, {})
        assert len(results["results"]) == 10  # i.e. 'rows' default value

    @pytest.mark.ckan_config("ckan.search.rows_max", "3")
    def test_rows_returned_limited(self):
        self._create_bulk_datasets("rows_limited", 5)
        results = logic.get_action("package_search")({}, {"rows": "15"})
        assert len(results["results"]) == 3  # i.e. ckan.search.rows_max

    def test_facets(self):
        org = factories.Organization(name="test-org-facet", title="Test Org")
        factories.Dataset(owner_org=org["id"])
        factories.Dataset(owner_org=org["id"])

        data_dict = {"facet.field": ["organization"]}
        search_result = helpers.call_action("package_search", **data_dict)

        assert search_result["count"] == 2
        assert search_result["search_facets"] == {
            "organization": {
                "items": [
                    {
                        "count": 2,
                        "display_name": "Test Org",
                        "name": "test-org-facet",
                    }
                ],
                "title": "organization",
            }
        }

    def test_facet_limit(self):
        group1 = factories.Group(name="test-group-fl1", title="Test Group 1")
        group2 = factories.Group(name="test-group-fl2", title="Test Group 2")
        factories.Dataset(groups=[{"name": group1["name"]}, {"name": group2["name"]}])
        factories.Dataset(groups=[{"name": group1["name"]}])
        factories.Dataset()

        data_dict = {"facet.field": ["groups"], "facet.limit": 1}
        search_result = helpers.call_action("package_search", **data_dict)

        assert len(search_result["search_facets"]["groups"]["items"]) == 1
        assert search_result["search_facets"] == {
            "groups": {
                "items": [
                    {
                        "count": 2,
                        "display_name": "Test Group 1",
                        "name": "test-group-fl1",
                    }
                ],
                "title": "groups",
            }
        }

    def test_facet_no_limit(self):
        group1 = factories.Group()
        group2 = factories.Group()
        factories.Dataset(groups=[{"name": group1["name"]}, {"name": group2["name"]}])
        factories.Dataset(groups=[{"name": group1["name"]}])
        factories.Dataset()

        data_dict = {"facet.field": ["groups"], "facet.limit": -1}  # no limit
        search_result = helpers.call_action("package_search", **data_dict)

        assert len(search_result["search_facets"]["groups"]["items"]) == 2

    def test_sort(self):
        factories.Dataset(name="test0")
        factories.Dataset(name="test1")
        factories.Dataset(name="test2")

        search_result = helpers.call_action(
            "package_search", sort="metadata_created desc"
        )

        result_names = [result["name"] for result in search_result["results"]]
        assert result_names == ["test2", "test1", "test0"]

    @pytest.mark.ckan_config("ckan.search.default_package_sort", "metadata_created asc")
    def test_sort_default_from_config(self):
        factories.Dataset(name="test0")
        factories.Dataset(name="test1")
        factories.Dataset(name="test2")

        search_result = helpers.call_action("package_search")

        result_names = [result["name"] for result in search_result["results"]]
        assert result_names == ["test0", "test1", "test2"]

    def test_package_search_on_resource_name(self):
        """
        package_search() should allow searching on resource name field.
        """
        resource_name = "resource_abc"
        factories.Resource(name=resource_name)

        search_result = helpers.call_action("package_search", q="resource_abc")
        assert search_result["results"][0]["resources"][0]["name"] == resource_name

    def test_package_search_excludes_private_and_drafts(self):
        """
        package_search() with no options should not return private and draft
        datasets.
        """
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user)
        factories.Dataset(user=user, state="deleted")
        factories.Dataset(user=user, state="draft")
        factories.Dataset(user=user, private=True, owner_org=org["name"])

        results = helpers.call_action("package_search")["results"]

        assert len(results) == 1
        assert results[0]["name"] == dataset["name"]

    def test_package_search_with_fq_excludes_private(self):
        """
        package_search() with fq capacity:private should not return private
        and draft datasets.
        """
        user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(user=user)
        factories.Dataset(user=user, state="deleted")
        factories.Dataset(user=user, state="draft")
        factories.Dataset(user=user, private=True, owner_org=org["name"])

        fq = "capacity:private"
        results = helpers.call_action("package_search", fq=fq)["results"]

        assert len(results) == 0

    def test_package_search_with_fq_excludes_drafts(self):
        """
        A sysadmin user can't use fq drafts to get draft datasets. Nothing is
        returned.
        """
        user = factories.User()
        other_user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(user=user, name="dataset")
        factories.Dataset(user=other_user, name="other-dataset")
        factories.Dataset(user=user, state="deleted", name="deleted-dataset")
        factories.Dataset(user=user, state="draft", name="draft-dataset")
        factories.Dataset(user=other_user, state="draft", name="other-draft-dataset")
        factories.Dataset(
            user=user,
            private=True,
            owner_org=org["name"],
            name="private-dataset",
        )

        fq = "state:draft"
        results = helpers.call_action("package_search", fq=fq)["results"]

        assert len(results) == 0

    def test_package_search_with_include_drafts_option_excludes_drafts_for_anon_user(
        self,
    ):
        """
        An anon user can't user include_drafts to get draft datasets.
        """
        user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user)
        factories.Dataset(user=user, state="deleted")
        draft_dataset = factories.Dataset(user=user, state="draft")
        factories.Dataset(user=user, private=True, owner_org=org["name"])

        results = logic.get_action("package_search")(
            {"user": ""}, {"include_drafts": True}
        )["results"]

        assert len(results) == 1
        assert results[0]["name"] != draft_dataset["name"]
        assert results[0]["name"] == dataset["name"]

    def test_package_search_with_include_drafts_option_includes_drafts_for_sysadmin(
        self,
    ):
        """
        A sysadmin can use the include_drafts option to get draft datasets for
        all users.
        """
        user = factories.User()
        other_user = factories.User()
        sysadmin = factories.Sysadmin()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user)
        factories.Dataset(user=user, state="deleted")
        draft_dataset = factories.Dataset(user=user, state="draft")
        other_draft_dataset = factories.Dataset(user=other_user, state="draft")
        factories.Dataset(user=user, private=True, owner_org=org["name"])

        results = logic.get_action("package_search")(
            {"user": sysadmin["name"]}, {"include_drafts": True}
        )["results"]

        assert len(results) == 3
        names = [r["name"] for r in results]
        assert draft_dataset["name"] in names
        assert other_draft_dataset["name"] in names
        assert dataset["name"] in names

    def test_package_search_with_include_drafts_false_option_doesnot_include_drafts_for_sysadmin(
        self,
    ):
        """
        A sysadmin with include_drafts option set to `False` will not get
        drafts returned in results.
        """
        user = factories.User()
        other_user = factories.User()
        sysadmin = factories.Sysadmin()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user)
        factories.Dataset(user=user, state="deleted")
        draft_dataset = factories.Dataset(user=user, state="draft")
        other_draft_dataset = factories.Dataset(user=other_user, state="draft")
        factories.Dataset(user=user, private=True, owner_org=org["name"])

        results = logic.get_action("package_search")(
            {"user": sysadmin["name"]}, {"include_drafts": False}
        )["results"]

        assert len(results) == 1
        names = [r["name"] for r in results]
        assert draft_dataset["name"] not in names
        assert other_draft_dataset["name"] not in names
        assert dataset["name"] in names

    def test_package_search_with_include_drafts_option_includes_drafts_for_user(
        self,
    ):
        """
        The include_drafts option will include draft datasets for the
        authorized user, but not drafts for other users.
        """
        user = factories.User()
        other_user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user, name="dataset")
        other_dataset = factories.Dataset(user=other_user, name="other-dataset")
        factories.Dataset(user=user, state="deleted", name="deleted-dataset")
        draft_dataset = factories.Dataset(
            user=user, state="draft", name="draft-dataset"
        )
        other_draft_dataset = factories.Dataset(
            user=other_user, state="draft", name="other-draft-dataset"
        )
        factories.Dataset(
            user=user,
            private=True,
            owner_org=org["name"],
            name="private-dataset",
        )

        results = logic.get_action("package_search")(
            {"user": user["name"]}, {"include_drafts": True}
        )["results"]

        assert len(results) == 3
        names = [r["name"] for r in results]
        assert draft_dataset["name"] in names
        assert other_draft_dataset["name"] not in names
        assert dataset["name"] in names
        assert other_dataset["name"] in names

    def test_package_search_with_fq_for_create_user_id_will_include_datasets_for_other_users(
        self,
    ):
        """
        A normal user can use the fq creator_user_id to get active datasets
        (but not draft) for another user.
        """
        user = factories.User()
        other_user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user, name="dataset")
        other_dataset = factories.Dataset(user=other_user, name="other-dataset")
        factories.Dataset(user=user, state="deleted", name="deleted-dataset")
        draft_dataset = factories.Dataset(
            user=user, state="draft", name="draft-dataset"
        )
        other_draft_dataset = factories.Dataset(
            user=other_user, state="draft", name="other-draft-dataset"
        )
        factories.Dataset(
            user=user,
            private=True,
            owner_org=org["name"],
            name="private-dataset",
        )

        fq = "creator_user_id:{0}".format(other_user["id"])
        results = logic.get_action("package_search")(
            {"user": user["name"]}, {"fq": fq}
        )["results"]

        assert len(results) == 1
        names = [r["name"] for r in results]
        assert draft_dataset["name"] not in names
        assert other_draft_dataset["name"] not in names
        assert dataset["name"] not in names
        assert other_dataset["name"] in names

    def test_package_search_with_fq_for_create_user_id_will_not_include_drafts_for_other_users(
        self,
    ):
        """
        A normal user can't use fq creator_user_id and drafts to get draft
        datasets for another user.
        """
        user = factories.User()
        other_user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(user=user, name="dataset")
        factories.Dataset(user=other_user, name="other-dataset")
        factories.Dataset(user=user, state="deleted", name="deleted-dataset")
        factories.Dataset(user=user, state="draft", name="draft-dataset")
        factories.Dataset(user=other_user, state="draft", name="other-draft-dataset")
        factories.Dataset(
            user=user,
            private=True,
            owner_org=org["name"],
            name="private-dataset",
        )

        fq = "(creator_user_id:{0} AND +state:draft)".format(other_user["id"])
        results = logic.get_action("package_search")(
            {"user": user["name"]}, {"fq": fq, "include_drafts": True}
        )["results"]

        assert len(results) == 0

    def test_package_search_with_fq_for_creator_user_id_and_drafts_and_include_drafts_option_will_not_include_drafts_for_other_user(
        self,
    ):
        """
        A normal user can't use fq creator_user_id and drafts and the
        include_drafts option to get draft datasets for another user.
        """
        user = factories.User()
        other_user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(user=user, name="dataset")
        factories.Dataset(user=other_user, name="other-dataset")
        factories.Dataset(user=user, state="deleted", name="deleted-dataset")
        factories.Dataset(user=user, state="draft", name="draft-dataset")
        factories.Dataset(user=other_user, state="draft", name="other-draft-dataset")
        factories.Dataset(
            user=user,
            private=True,
            owner_org=org["name"],
            name="private-dataset",
        )

        fq = "(creator_user_id:{0} AND +state:draft)".format(other_user["id"])
        results = logic.get_action("package_search")(
            {"user": user["name"]}, {"fq": fq, "include_drafts": True}
        )["results"]

        assert len(results) == 0

    def test_package_search_with_fq_for_creator_user_id_and_include_drafts_option_will_not_include_drafts_for_other_user(
        self,
    ):
        """
        A normal user can't use fq creator_user_id and the include_drafts
        option to get draft datasets for another user.
        """
        user = factories.User()
        other_user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(user=user, name="dataset")
        other_dataset = factories.Dataset(user=other_user, name="other-dataset")
        factories.Dataset(user=user, state="deleted", name="deleted-dataset")
        factories.Dataset(user=user, state="draft", name="draft-dataset")
        other_draft_dataset = factories.Dataset(
            user=other_user, state="draft", name="other-draft-dataset"
        )
        factories.Dataset(
            user=user,
            private=True,
            owner_org=org["name"],
            name="private-dataset",
        )

        fq = "creator_user_id:{0}".format(other_user["id"])
        results = logic.get_action("package_search")(
            {"user": user["name"]}, {"fq": fq, "include_drafts": True}
        )["results"]

        names = [r["name"] for r in results]
        assert len(results) == 1
        assert other_dataset["name"] in names
        assert other_draft_dataset["name"] not in names

    def test_package_search_with_fq_for_create_user_id_will_include_drafts_for_other_users_for_sysadmin(
        self,
    ):
        """
        Sysadmins can use fq to get draft datasets for another user.
        """
        user = factories.User()
        sysadmin = factories.Sysadmin()
        other_user = factories.User()
        org = factories.Organization(user=user)
        dataset = factories.Dataset(user=user, name="dataset")
        factories.Dataset(user=other_user, name="other-dataset")
        factories.Dataset(user=user, state="deleted", name="deleted-dataset")
        draft_dataset = factories.Dataset(
            user=user, state="draft", name="draft-dataset"
        )
        factories.Dataset(user=other_user, state="draft", name="other-draft-dataset")
        factories.Dataset(
            user=user,
            private=True,
            owner_org=org["name"],
            name="private-dataset",
        )

        fq = "(creator_user_id:{0} AND +state:draft)".format(user["id"])
        results = logic.get_action("package_search")(
            {"user": sysadmin["name"]}, {"fq": fq}
        )["results"]

        names = [r["name"] for r in results]
        assert len(results) == 1
        assert dataset["name"] not in names
        assert draft_dataset["name"] in names

    def test_package_search_private_with_include_private(self):
        """
        package_search() can return private datasets when
        `include_private=True`
        """
        user = factories.User()
        org = factories.Organization(user=user)
        factories.Dataset(user=user, state="deleted")
        factories.Dataset(user=user, state="draft")
        private_dataset = factories.Dataset(
            user=user, private=True, owner_org=org["name"]
        )

        results = logic.get_action("package_search")(
            {"user": user["name"]}, {"include_private": True}
        )["results"]

        assert [r["name"] for r in results] == [private_dataset["name"]]

    @pytest.mark.parametrize("remove_deleted_setting", [True, False])
    def test_package_search_private_with_include_private_wont_show_other_orgs_private(
        self, remove_deleted_setting
    ):
        with helpers.changed_config(
            "ckan.search.remove_deleted_packages", remove_deleted_setting
        ):
            user = factories.User()
            user2 = factories.User()
            factories.Organization(user=user)
            org2 = factories.Organization(user=user2)
            # create a deleted dataset if we expect them to be indexed
            factories.Dataset(
                user=user2,
                private=True,
                owner_org=org2["name"],
                state="active" if remove_deleted_setting else "deleted",
            )

            # include deleted datasets if we expect them to be indexed
            results = logic.get_action("package_search")(
                {"user": user["name"]},
                {
                    "include_private": True,
                    "include_deleted": not remove_deleted_setting,
                },
            )["results"]

            assert [r["name"] for r in results] == []

    @pytest.mark.parametrize("remove_deleted_setting", [True, False])
    def test_package_search_private_with_include_private_syadmin(
        self, remove_deleted_setting
    ):
        with helpers.changed_config(
            "ckan.search.remove_deleted_packages", remove_deleted_setting
        ):
            user = factories.User()
            sysadmin = factories.Sysadmin()
            org = factories.Organization(user=user)
            # create a deleted dataset if we expect them to be indexed
            private_dataset = factories.Dataset(
                user=user,
                private=True,
                owner_org=org["name"],
                state="active" if remove_deleted_setting else "deleted",
            )

            # include deleted datasets if we expect them to be indexed
            results = logic.get_action("package_search")(
                {"user": sysadmin["name"]},
                {
                    "include_private": True,
                    "include_deleted": not remove_deleted_setting,
                },
            )["results"]

            assert [r["name"] for r in results] == [private_dataset["name"]]

    def test_package_works_without_user_in_context(self):
        """
        package_search() should work even if user isn't in the context (e.g.
        ckanext-showcase tests.
        """
        logic.get_action("package_search")({}, dict(q="anything"))

    def test_local_parameters_not_supported(self):
        with pytest.raises(SearchError):
            helpers.call_action(
                "package_search", q='{!child of="content_type:parentDoc"}'
            )


@pytest.mark.ckan_config("ckan.plugins", "example_idatasetform")
@pytest.mark.usefixtures("clean_db", "with_plugins")
def test_custom_schema_returned():
    dataset1 = factories.Dataset(custom_text="foo")

    query = helpers.call_action("package_search", q="id:{0}".format(dataset1["id"]))

    assert query["results"][0]["id"] == dataset1["id"]
    assert query["results"][0]["custom_text"] == "foo"


@pytest.mark.ckan_config("ckan.plugins", "example_idatasetform")
@pytest.mark.usefixtures("clean_db", "with_plugins")
def test_custom_schema_not_returned():
    dataset1 = factories.Dataset(custom_text="foo")

    query = helpers.call_action(
        "package_search",
        q="id:{0}".format(dataset1["id"]),
        use_default_schema=True,
    )

    assert query["results"][0]["id"] == dataset1["id"]
    assert "custom_text" not in query["results"][0]
    assert query["results"][0]["extras"][0]["key"] == "custom_text"
    assert query["results"][0]["extras"][0]["value"] == "foo"


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_missing_param():
    with pytest.raises(logic.ValidationError):
        helpers.call_action("format_autocomplete")


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_autocomplete():
    result = helpers.call_action("format_autocomplete", q="cs")
    assert result == []
    factories.Resource(format="CSV")
    result = helpers.call_action("format_autocomplete", q="cs")
    assert result == ["csv"]


@pytest.mark.usefixtures("clean_db")
class TestBadLimitQueryParameters(object):
    """test class for #1258 non-int query parameters cause 500 errors

    Test that validation errors are raised when calling actions with
    bad parameters.
    """

    def test_package_search_facet_field_is_json(self):
        kwargs = {"facet.field": "notjson"}
        with pytest.raises(logic.ValidationError):
            helpers.call_action("package_search", **kwargs)


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", False)
def test_package_collaborator_list_when_config_disabled():

    dataset = factories.Dataset()

    with pytest.raises(logic.ValidationError):
        helpers.call_action("package_collaborator_list", id=dataset["id"])


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_list():

    dataset = factories.Dataset()
    user1 = factories.User()
    capacity1 = "editor"
    user2 = factories.User()
    capacity2 = "member"

    helpers.call_action(
        "package_collaborator_create",
        id=dataset["id"],
        user_id=user1["id"],
        capacity=capacity1,
    )

    helpers.call_action(
        "package_collaborator_create",
        id=dataset["id"],
        user_id=user2["id"],
        capacity=capacity2,
    )

    members = helpers.call_action("package_collaborator_list", id=dataset["id"])

    assert len(members) == 2

    assert members[0]["package_id"] == dataset["id"]
    assert members[0]["user_id"] == user1["id"]
    assert members[0]["capacity"] == capacity1

    assert members[1]["package_id"] == dataset["id"]
    assert members[1]["user_id"] == user2["id"]
    assert members[1]["capacity"] == capacity2


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_list_with_capacity():

    dataset = factories.Dataset()
    user1 = factories.User()
    capacity1 = "editor"
    user2 = factories.User()
    capacity2 = "member"

    helpers.call_action(
        "package_collaborator_create",
        id=dataset["id"],
        user_id=user1["id"],
        capacity=capacity1,
    )

    helpers.call_action(
        "package_collaborator_create",
        id=dataset["id"],
        user_id=user2["id"],
        capacity=capacity2,
    )

    members = helpers.call_action(
        "package_collaborator_list", id=dataset["id"], capacity="member"
    )

    assert len(members) == 1

    assert members[0]["package_id"] == dataset["id"]
    assert members[0]["user_id"] == user2["id"]
    assert members[0]["capacity"] == capacity2


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_list_dataset_not_found():

    with pytest.raises(logic.NotFound):
        helpers.call_action("package_collaborator_list", id="xxx")


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_list_wrong_capacity():
    dataset = factories.Dataset()
    user = factories.User()
    capacity = "unknown"

    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "package_collaborator_list",
            id=dataset["id"],
            user_id=user["id"],
            capacity=capacity,
        )


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_list_for_user():

    dataset1 = factories.Dataset()
    dataset2 = factories.Dataset()
    user = factories.User()
    capacity1 = "editor"
    capacity2 = "member"

    helpers.call_action(
        "package_collaborator_create",
        id=dataset1["id"],
        user_id=user["id"],
        capacity=capacity1,
    )

    helpers.call_action(
        "package_collaborator_create",
        id=dataset2["id"],
        user_id=user["id"],
        capacity=capacity2,
    )

    datasets = helpers.call_action("package_collaborator_list_for_user", id=user["id"])

    assert len(datasets) == 2

    assert datasets[0]["package_id"] == dataset1["id"]
    assert datasets[0]["capacity"] == capacity1

    assert datasets[1]["package_id"] == dataset2["id"]
    assert datasets[1]["capacity"] == capacity2


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_list_for_user_with_capacity():

    dataset1 = factories.Dataset()
    dataset2 = factories.Dataset()
    user = factories.User()
    capacity1 = "editor"
    capacity2 = "member"

    helpers.call_action(
        "package_collaborator_create",
        id=dataset1["id"],
        user_id=user["id"],
        capacity=capacity1,
    )

    helpers.call_action(
        "package_collaborator_create",
        id=dataset2["id"],
        user_id=user["id"],
        capacity=capacity2,
    )

    datasets = helpers.call_action(
        "package_collaborator_list_for_user",
        id=user["id"],
        capacity="editor",
    )

    assert len(datasets) == 1

    assert datasets[0]["package_id"] == dataset1["id"]
    assert datasets[0]["capacity"] == capacity1


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_list_for_user_user_not_found():

    with pytest.raises(logic.NotAuthorized):
        helpers.call_action("package_collaborator_list_for_user", id="xxx")


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_list_for_user_wrong_capacity():
    user = factories.User()
    capacity = "unknown"

    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "package_collaborator_list_for_user",
            id=user["id"],
            capacity=capacity,
        )


@pytest.mark.usefixtures("clean_db", "clean_index")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_search_results_editor():

    org = factories.Organization()
    dataset1 = factories.Dataset(name="test1", private=True, owner_org=org["id"])
    dataset2 = factories.Dataset(name="test2")

    user = factories.User()
    context = {"user": user["name"], "ignore_auth": False}

    results = helpers.call_action(
        "package_search", context=context, q="*:*", include_private=True
    )

    assert results["count"] == 1
    assert results["results"][0]["id"] == dataset2["id"]

    helpers.call_action(
        "package_collaborator_create",
        id=dataset1["id"],
        user_id=user["id"],
        capacity="editor",
    )

    results = helpers.call_action(
        "package_search",
        context=context,
        q="*:*",
        include_private=True,
        sort="name asc",
    )

    assert results["count"] == 2

    assert results["results"][0]["id"] == dataset1["id"]
    assert results["results"][1]["id"] == dataset2["id"]


@pytest.mark.usefixtures("clean_db", "clean_index")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_search_results_member():

    org = factories.Organization()
    dataset1 = factories.Dataset(name="test1", private=True, owner_org=org["id"])
    dataset2 = factories.Dataset(name="test2")

    user = factories.User()
    context = {"user": user["name"], "ignore_auth": False}

    results = helpers.call_action(
        "package_search", context=context, q="*:*", include_private=True
    )

    assert results["count"] == 1
    assert results["results"][0]["id"] == dataset2["id"]

    helpers.call_action(
        "package_collaborator_create",
        id=dataset1["id"],
        user_id=user["id"],
        capacity="member",
    )

    results = helpers.call_action(
        "package_search",
        context=context,
        q="*:*",
        include_private=True,
        sort="name asc",
    )

    assert results["count"] == 2

    assert results["results"][0]["id"] == dataset1["id"]
    assert results["results"][1]["id"] == dataset2["id"]


@pytest.mark.usefixtures("clean_db", "clean_index")
@pytest.mark.usefixtures("app")
def test_package_list():
    pkg1 = factories.Dataset()
    pkg2 = factories.Dataset()
    packages = helpers.call_action("package_list")
    assert len(packages) == 2
    assert set(packages) == {pkg1["name"], pkg2["name"]}


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_package_list_private():
    org = factories.Organization()
    pkg1 = factories.Dataset()
    factories.Dataset(private=True, owner_org=org["id"])
    packages = helpers.call_action("package_list")
    assert packages == [pkg1["name"]]


@pytest.mark.usefixtures("clean_db")
def test_returned_if_sysadmin_and_include_plugin_data_only():
    sysadmin = factories.Sysadmin()
    user = factories.User()

    dataset = factories.Dataset(plugin_data={"plugin1": {"key1": "value1"}})
    context = {
        "user": sysadmin["name"],
        "ignore_auth": False,
        "auth_user_obj": model.User.get(sysadmin["name"]),
    }
    # sysadmin and include_plugin_data = True
    pkg_dict = helpers.call_action(
        "package_show", context=context, id=dataset["id"], include_plugin_data=True
    )
    assert pkg_dict["plugin_data"] == {"plugin1": {"key1": "value1"}}

    # sysadmin and include_plugin_data = False
    pkg_dict = helpers.call_action("package_show", context=context, id=dataset["id"])
    assert "plugin_data" not in pkg_dict

    # non-sysadmin and include_plugin_data = True
    context = {
        "user": user["name"],
        "ignore_auth": False,
    }
    pkg_dict = helpers.call_action(
        "package_show", context=context, id=dataset["id"], include_plugin_data=True
    )
    assert "plugin_data" not in pkg_dict


@pytest.mark.usefixtures("non_clean_db")
def test_package_patch_updating_single_field():
    user = factories.User()
    dataset = factories.Dataset(notes="some test now", user=user)
    stub = factories.Dataset.stub()
    dataset = helpers.call_action("package_patch", id=dataset["id"], name=stub.name)

    assert dataset["name"] == stub.name
    assert dataset["notes"] == "some test now"

    dataset2 = helpers.call_action("package_show", id=dataset["id"])

    assert dataset2["name"] == stub.name
    assert dataset2["notes"] == "some test now"


@pytest.mark.usefixtures("non_clean_db")
def test_package_patch_invalid_characters_in_resource_id():
    user = factories.User()
    dataset = factories.Dataset(user=user)

    with pytest.raises(ValidationError):
        helpers.call_action(
            "package_patch",
            id=dataset["id"],
            resources=[
                {
                    "id": "../../nope.txt",
                    "url": "http://data",
                    "name": "A nice resource",
                },
            ],
        )


@pytest.mark.usefixtures("non_clean_db")
def test_package_patch_for_update():

    dataset = factories.Dataset()

    mock_package_show = mock.MagicMock()
    mock_package_show.side_effect = lambda context, data_dict: core_package_show(
        context, data_dict
    )

    with mock.patch.dict("ckan.logic._actions", {"package_show": mock_package_show}):
        helpers.call_action("package_patch", id=dataset["id"], notes="hey")
        assert mock_package_show.call_args_list[0][0][0].get("for_update") is True


@pytest.mark.usefixtures("non_clean_db")
class TestUpdatePackage(object):
    def teardown(self):
        # Since some of the test methods below use the mock module to patch
        # things, we use this teardown() method to remove remove all patches.
        # (This makes sure the patches always get removed even if the test
        # method aborts with an exception or something.)
        mock.patch.stopall()

    def test_update_dataset_cant_change_type(self):
        user = factories.User()
        dataset = factories.Dataset(type="dataset", name="unchanging", user=user)

        dataset = helpers.call_action(
            "package_update",
            id=dataset["id"],
            name="unchanging",
            type="cabinet",
        )

        assert dataset["type"] == "dataset"
        assert helpers.call_action("package_show", id="unchanging")["type"] == "dataset"


@pytest.mark.usefixtures("non_clean_db")
def test_datasetupdate_missing_id():
    user = factories.User()
    factories.Dataset(user=user)

    with pytest.raises(logic.ValidationError):
        helpers.call_action("package_update")


@pytest.mark.usefixtures("non_clean_db")
def test_datasetupdate_name():
    user = factories.User()
    dataset = factories.Dataset(user=user)

    stub = factories.Dataset.stub()
    with freeze_time("2020-02-25 12:00:00"):
        updated = helpers.call_action(
            "package_update", id=dataset["id"], name=stub.name
        )
    assert updated["name"] == stub.name
    assert updated["metadata_modified"] == "2020-02-25T12:00:00"
    assert updated == helpers.call_action("package_show", id=dataset["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_datasetupdate_title():
    user = factories.User()
    dataset = factories.Dataset(user=user)

    with freeze_time("2020-02-25 12:00:00"):
        updated = helpers.call_action(
            "package_update", id=dataset["id"], title="New Title"
        )
    assert updated["title"] == "New Title"
    assert updated["metadata_modified"] == "2020-02-25T12:00:00"
    assert updated == helpers.call_action("package_show", id=dataset["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_datasetupdate_extras():
    user = factories.User()
    dataset = factories.Dataset(user=user)

    with freeze_time("2020-02-25 12:00:00"):
        updated = helpers.call_action(
            "package_update",
            id=dataset["id"],
            extras=[{"key": "original media", "value": '"book"'}],
        )
    assert updated["extras"][0]["key"] == "original media"
    assert updated["extras"][0]["value"] == '"book"'
    assert updated["metadata_modified"] == "2020-02-25T12:00:00"
    assert updated == helpers.call_action("package_show", id=dataset["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_extra_can_be_restored_after_deletion():
    user = factories.User()
    dataset = factories.Dataset(user=user)

    with freeze_time("2020-02-25 12:00:00"):
        updated = helpers.call_action(
            "package_update",
            id=dataset["id"],
            extras=[
                {"key": "old attribute", "value": "value"},
                {"key": "original media", "value": '"book"'},
            ],
        )
    assert len(updated["extras"]) == 2
    assert updated["metadata_modified"] == "2020-02-25T12:00:00"

    with freeze_time("2023-03-23 13:00:00"):
        updated2 = helpers.call_action(
            "package_update",
            id=dataset["id"],
            extras=[],
        )
    assert updated2["extras"] == []
    assert updated2["metadata_modified"] == "2023-03-23T13:00:00"

    with freeze_time("2024-04-24 14:00:00"):
        updated3 = helpers.call_action(
            "package_update",
            id=dataset["id"],
            extras=[
                {"key": "original media", "value": '"book"'},
                {"key": "new attribute", "value": "value"},
            ],
        )
    assert len(updated3["extras"]) == 2
    assert updated3["metadata_modified"] == "2024-04-24T14:00:00"


@pytest.mark.usefixtures("non_clean_db")
def test_datasetupdate_license():
    user = factories.User()
    dataset = factories.Dataset(user=user)

    with freeze_time("2020-02-25 12:00:00"):
        updated = helpers.call_action(
            "package_update", id=dataset["id"], license_id="other-open"
        )
    assert updated["license_id"] == "other-open"
    assert updated["metadata_modified"] == "2020-02-25T12:00:00"
    assert updated == helpers.call_action("package_show", id=dataset["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_datasetupdate_notes():
    user = factories.User()
    dataset = factories.Dataset(user=user)

    with freeze_time("2020-02-25 12:00:00"):
        updated = helpers.call_action(
            "package_update", id=dataset["id"], notes="some notes"
        )
    assert updated["notes"] == "some notes"
    assert updated["metadata_modified"] == "2020-02-25T12:00:00"
    assert updated == helpers.call_action("package_show", id=dataset["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_datasetupdate_resources():
    user = factories.User()
    dataset = factories.Dataset(user=user)

    with freeze_time("2020-02-25 12:00:00"):
        updated = helpers.call_action(
            "package_update",
            id=dataset["id"],
            resources=[
                {
                    "alt_url": "alt123",
                    "description": "Full text.",
                    "somekey": "somevalue",  # correct resource extras
                    "extras": {"someotherkey": "alt234"},  # this isn't
                    "format": "plain text",
                    "hash": "abc123",
                    "position": 0,
                    "url": "http://datahub.io/download/",
                },
                {
                    "description": "Index of the novel",
                    "format": "JSON",
                    "position": 1,
                    "url": "http://datahub.io/index.json",
                },
            ],
        )
    assert updated["metadata_modified"] == "2020-02-25T12:00:00"
    resources_ = updated["resources"]
    assert resources_[0]["alt_url"] == "alt123"
    assert resources_[0]["description"] == "Full text."
    assert resources_[0]["somekey"] == "somevalue"
    assert "extras" not in resources_[0]
    assert "someotherkey" not in resources_[0]
    assert resources_[0]["format"] == "plain text"
    assert resources_[0]["hash"] == "abc123"
    assert resources_[0]["position"] == 0
    assert resources_[0]["url"] == "http://datahub.io/download/"
    assert resources_[0]["metadata_modified"] == "2020-02-25T12:00:00"
    assert resources_[1]["description"] == "Index of the novel"
    assert resources_[1]["format"] == "JSON"
    assert resources_[1]["url"] == "http://datahub.io/index.json"
    assert resources_[1]["position"] == 1
    assert resources_[1]["metadata_modified"] == "2020-02-25T12:00:00"
    assert (
        helpers.call_action("package_show", id=dataset["id"])["resources"] == resources_
    )


@pytest.mark.usefixtures("non_clean_db")
def test_invalid_characters_in_resource_id():
    user = factories.User()
    dataset = factories.Dataset(user=user)

    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "package_update",
            id=dataset["id"],
            resources=[
                {
                    "id": "../../nope.txt",
                    "url": "http://data",
                    "name": "A nice resource",
                },
            ],
        )


@pytest.mark.usefixtures("non_clean_db")
def test_datasetupdate_tags():
    user = factories.User()
    dataset = factories.Dataset(user=user)
    tag1 = factories.Tag.stub().name
    tag2 = factories.Tag.stub().name
    with freeze_time("2020-02-25 12:00:00"):
        updated = helpers.call_action(
            "package_update",
            id=dataset["id"],
            tags=[{"name": tag1}, {"name": tag2}],
        )
    assert updated["metadata_modified"] == "2020-02-25T12:00:00"
    tag_names = sorted(tag_dict["name"] for tag_dict in updated["tags"])
    assert tag_names == sorted([tag1, tag2])
    assert updated == helpers.call_action("package_show", id=dataset["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_datasetupdate_return_id_only():
    user = factories.User()
    dataset = factories.Dataset(user=user)

    updated_dataset = helpers.call_action(
        "package_update",
        id=dataset["id"],
        notes="Test",
        context={"return_id_only": True},
    )

    assert updated_dataset == dataset["id"]


@pytest.mark.usefixtures("non_clean_db")
def test_resources_unchanged_if_missing():
    res = factories.Resource()

    with freeze_time("2020-02-25 12:00:00"):
        updated_dataset = helpers.call_action(
            "package_update",
            id=res["package_id"],
            notes="hi",
        )
    assert updated_dataset["metadata_modified"] == "2020-02-25T12:00:00"
    assert updated_dataset["resources"] == [res]


@pytest.mark.usefixtures("non_clean_db")
def test_resources_removed_if_empty_list():
    res = factories.Resource()

    with freeze_time("2020-02-25 12:00:00"):
        updated_dataset = helpers.call_action(
            "package_update",
            id=res["package_id"],
            notes="hi",
            resources=[],
        )
    assert updated_dataset["metadata_modified"] == "2020-02-25T12:00:00"
    assert updated_dataset["resources"] == []


@pytest.mark.usefixtures("non_clean_db")
def test_tags_removed_if_missing():
    dataset = factories.Dataset(tag_string="tagone,tagtwo")
    assert dataset["tags"]

    with freeze_time("2020-02-25 12:00:00"):
        updated_dataset = helpers.call_action(
            "package_update",
            id=dataset["id"],
        )
    assert updated_dataset["metadata_modified"] == "2020-02-25T12:00:00"
    assert updated_dataset["tags"] == []


@pytest.mark.usefixtures("non_clean_db")
def test_groups_unchanged_if_missing():
    group = factories.Group()
    dataset = factories.Dataset(groups=[group])
    assert dataset["groups"]

    with freeze_time("2020-02-25 12:00:00"):
        updated_dataset = helpers.call_action(
            "package_update",
            id=dataset["id"],
        )
    assert updated_dataset["metadata_modified"] == "2020-02-25T12:00:00"
    assert updated_dataset["groups"] == dataset["groups"]


@pytest.mark.usefixtures("non_clean_db")
def test_groups_removed_if_empty_list():
    group = factories.Group()
    dataset = factories.Dataset(groups=[group])
    assert dataset["groups"]

    with freeze_time("2020-02-25 12:00:00"):
        updated_dataset = helpers.call_action(
            "package_update",
            id=dataset["id"],
            groups=[],
        )
    assert updated_dataset["metadata_modified"] == "2020-02-25T12:00:00"
    assert updated_dataset["groups"] == []


@pytest.mark.usefixtures("non_clean_db")
def test_metadata_modified_unchanged_on_no_changes():
    with freeze_time("2020-02-25 12:00:00"):
        dataset = factories.Dataset()

    # allow metadata_modified update
    dataset.pop("metadata_modified")
    updated_dataset = helpers.call_action("package_update", **dataset)
    assert updated_dataset["metadata_modified"] == "2020-02-25T12:00:00"

    # unchanged even if the json differs but results in the same
    # values in the db
    assert dataset.pop("owner_org") is None
    assert dataset.pop("tags") == []
    assert dataset.pop("resources") == []
    updated_dataset = helpers.call_action("package_update", **dataset)
    assert updated_dataset["metadata_modified"] == "2020-02-25T12:00:00"


@pytest.mark.usefixtures("non_clean_db")
def test_metadata_modified_can_be_updated():
    dataset = factories.Dataset()
    updated_dataset = helpers.call_action(
        "package_update", **dict(dataset, metadata_modified="2020-02-25T12:00:00")
    )
    assert updated_dataset["metadata_modified"] == "2020-02-25T12:00:00"

    # but not for normal users
    user = factories.User()
    context = {"user": user["name"], "ignore_auth": False}
    unchanged = helpers.call_action(
        "package_update",
        context,
        **dict(dataset, metadata_modified="2021-01-01T11:01:00"),
    )
    assert unchanged["metadata_modified"] == "2020-02-25T12:00:00"


@pytest.mark.usefixtures("non_clean_db")
@mock.patch("ckan.logic.index_update_package")
def test_reindex(index_update_package_mock):
    # test that authorized users can trigger a reindex
    dataset = factories.Dataset()
    dataset_id = dataset["id"]
    helpers.call_action("package_reindex", id=dataset_id)
    index_update_package_mock.assert_called()
    assert index_update_package_mock.call_args[0][1] == dataset_id

    # missing ID
    with pytest.raises(logic.ValidationError):
        helpers.call_action("package_reindex")

    # invalid ID
    with pytest.raises(logic.NotFound):
        helpers.call_action("package_reindex", id="nonexistent")


@pytest.mark.usefixtures("non_clean_db")
def test_package_owner_org_added():
    """A package without an owner_org can have one added."""
    sysadmin = factories.Sysadmin()
    org = factories.Organization()
    dataset = factories.Dataset()
    context = {"user": sysadmin["name"]}
    assert dataset["owner_org"] is None
    helpers.call_action(
        "package_owner_org_update",
        context=context,
        id=dataset["id"],
        organization_id=org["id"],
    )
    dataset_obj = model.Package.get(dataset["id"])
    assert dataset_obj.owner_org == org["id"]


@pytest.mark.usefixtures("non_clean_db")
def test_package_owner_org_changed():
    """A package with an owner_org can have it changed."""

    sysadmin = factories.Sysadmin()
    org_1 = factories.Organization()
    org_2 = factories.Organization()
    dataset = factories.Dataset(owner_org=org_1["id"])
    context = {"user": sysadmin["name"]}
    assert dataset["owner_org"] == org_1["id"]
    helpers.call_action(
        "package_owner_org_update",
        context=context,
        id=dataset["id"],
        organization_id=org_2["id"],
    )
    dataset_obj = model.Package.get(dataset["id"])
    assert dataset_obj.owner_org == org_2["id"]


@pytest.mark.usefixtures("non_clean_db")
def test_package_owner_org_removed():
    """A package with an owner_org can have it removed."""
    sysadmin = factories.Sysadmin()
    org = factories.Organization()
    dataset = factories.Dataset(owner_org=org["id"])
    context = {"user": sysadmin["name"]}
    assert dataset["owner_org"] == org["id"]
    helpers.call_action(
        "package_owner_org_update",
        context=context,
        id=dataset["id"],
        organization_id=None,
    )
    dataset_obj = model.Package.get(dataset["id"])
    assert dataset_obj.owner_org is None


@pytest.mark.usefixtures("non_clean_db")
def test_bulk_make_private():

    org = factories.Organization()

    dataset1 = factories.Dataset(owner_org=org["id"])
    dataset2 = factories.Dataset(owner_org=org["id"])

    helpers.call_action(
        "bulk_update_private",
        {},
        datasets=[dataset1["id"], dataset2["id"]],
        org_id=org["id"],
    )

    # Check search index
    datasets = helpers.call_action(
        "package_search", {}, q="owner_org:{0}".format(org["id"])
    )

    for dataset in datasets["results"]:
        assert dataset["private"]

    # Check DB
    datasets = (
        model.Session.query(model.Package)
        .filter(model.Package.owner_org == org["id"])
        .all()
    )
    for dataset in datasets:
        assert dataset.private


@pytest.mark.usefixtures("non_clean_db")
def test_bulk_make_public():

    org = factories.Organization()

    dataset1 = factories.Dataset(owner_org=org["id"], private=True)
    dataset2 = factories.Dataset(owner_org=org["id"], private=True)

    helpers.call_action(
        "bulk_update_public",
        {},
        datasets=[dataset1["id"], dataset2["id"]],
        org_id=org["id"],
    )

    # Check search index
    datasets = helpers.call_action(
        "package_search", {}, q="owner_org:{0}".format(org["id"])
    )

    for dataset in datasets["results"]:
        assert not (dataset["private"])

    # Check DB
    datasets = (
        model.Session.query(model.Package)
        .filter(model.Package.owner_org == org["id"])
        .all()
    )
    for dataset in datasets:
        assert not (dataset.private)


@pytest.mark.usefixtures("non_clean_db")
def test_bulk_delete():

    org = factories.Organization()

    dataset1 = factories.Dataset(owner_org=org["id"])
    dataset2 = factories.Dataset(owner_org=org["id"])

    helpers.call_action(
        "bulk_update_delete",
        {},
        datasets=[dataset1["id"], dataset2["id"]],
        org_id=org["id"],
    )

    # Check search index
    datasets = helpers.call_action(
        "package_search", {}, q="owner_org:{0}".format(org["id"])
    )

    assert datasets["results"] == []

    # Check DB
    datasets = (
        model.Session.query(model.Package)
        .filter(model.Package.owner_org == org["id"])
        .all()
    )
    for dataset in datasets:
        assert dataset.state == "deleted"


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
@pytest.mark.ckan_config("ckan.auth.allow_admin_collaborators", True)
@pytest.mark.parametrize("role", ["admin", "editor"])
def test_collaborators_can_update_resources(role):

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

    updated_resource = helpers.call_action(
        "resource_update",
        context=context,
        id=resource["id"],
        description="updated",
    )

    assert updated_resource["description"] == "updated"


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
def test_collaborators_can_not_change_owner_org_by_default():

    org1 = factories.Organization()
    dataset = factories.Dataset(owner_org=org1["id"])

    user = factories.User()
    org2 = factories.Organization(users=[{"name": user["id"], "capacity": "admin"}])

    helpers.call_action(
        "package_collaborator_create",
        id=dataset["id"],
        user_id=user["id"],
        capacity="editor",
    )

    context = {
        "user": user["name"],
        "ignore_auth": False,
    }

    dataset["owner_org"] = org2["id"]

    with pytest.raises(logic.ValidationError) as e:
        helpers.call_action("package_update", context=context, **dataset)

    assert e.value.error_dict["owner_org"] == [
        "You cannot move this dataset to another organization"
    ]


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
@pytest.mark.ckan_config("ckan.auth.allow_collaborators_to_change_owner_org", True)
def test_collaborators_can_change_owner_org_if_config_true():
    org1 = factories.Organization()
    dataset = factories.Dataset(owner_org=org1["id"])

    user = factories.User()
    org2 = factories.Organization(users=[{"name": user["id"], "capacity": "admin"}])

    helpers.call_action(
        "package_collaborator_create",
        id=dataset["id"],
        user_id=user["id"],
        capacity="editor",
    )

    context = {
        "user": user["name"],
        "ignore_auth": False,
    }

    dataset["owner_org"] = org2["id"]

    updated_dataset = helpers.call_action("package_update", context=context, **dataset)

    assert updated_dataset["owner_org"] == org2["id"]


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
@pytest.mark.ckan_config("ckan.auth.allow_collaborators_to_change_owner_org", True)
def test_editors_can_change_owner_org_even_if_collaborators():

    user = factories.User()

    org1 = factories.Organization(users=[{"name": user["id"], "capacity": "admin"}])
    dataset = factories.Dataset(owner_org=org1["id"])

    org2 = factories.Organization(users=[{"name": user["id"], "capacity": "admin"}])

    helpers.call_action(
        "package_collaborator_create",
        id=dataset["id"],
        user_id=user["id"],
        capacity="editor",
    )

    context = {
        "user": user["name"],
        "ignore_auth": False,
    }

    dataset["owner_org"] = org2["id"]

    updated_dataset = helpers.call_action("package_update", context=context, **dataset)

    assert updated_dataset["owner_org"] == org2["id"]


@pytest.mark.usefixtures("non_clean_db")
def test_revise_description():
    dataset = factories.Dataset(notes="old notes")
    response = helpers.call_action(
        "package_revise",
        match={"notes": "old notes", "name": dataset["name"]},
        update={"notes": "new notes"},
    )
    assert response["package"]["notes"] == "new notes"


@pytest.mark.usefixtures("non_clean_db")
def test_revise_failed_match():
    dataset = factories.Dataset(notes="old notes")
    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "package_revise",
            match={"notes": "wrong notes", "name": dataset["name"]},
            update={"notes": "new notes"},
        )


@pytest.mark.usefixtures("non_clean_db")
def test_revise_description_flattened():
    dataset = factories.Dataset(notes="old notes")
    response = helpers.call_action(
        "package_revise",
        match__notes="old notes",
        match__name=dataset["name"],
        update__notes="new notes",
    )
    assert response["package"]["notes"] == "new notes"


@pytest.mark.usefixtures("non_clean_db")
def test_revise_dataset_fields_only():
    dataset = factories.Dataset(
        notes="old notes",
        resources=[{"url": "http://example.com"}],
    )
    stub = factories.Dataset.stub()
    response = helpers.call_action(
        "package_revise",
        match={"id": dataset["id"]},
        filter=[
            "+resources",  # keep everything under resources
            "-*",  # remove everything else
        ],
        update={"name": stub.name, "title": "Fresh Start"},
    )
    assert response["package"]["notes"] is None
    assert response["package"]["name"] == stub.name
    assert response["package"]["resources"][0]["url"] == "http://example.com"


@pytest.mark.usefixtures("non_clean_db")
def test_revise_add_resource():
    dataset = factories.Dataset()
    response = helpers.call_action(
        "package_revise",
        match={"id": dataset["id"]},
        update__resources__extend=[
            {"name": "new resource", "url": "http://example.com"}
        ],
    )
    assert response["package"]["resources"][0]["name"] == "new resource"


@pytest.mark.usefixtures("non_clean_db")
def test_revise_invalid_resource_id():
    dataset = factories.Dataset()
    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "package_revise",
            match={"id": dataset["id"]},
            update__resources__extend=[
                {
                    "id": "../../nope.txt",
                    "name": "new resource",
                    "url": "http://example.com",
                }
            ],
        )


@pytest.mark.usefixtures("non_clean_db")
def test_revise_resource_by_index():
    dataset = factories.Dataset(resources=[{"url": "http://example.com"}])
    response = helpers.call_action(
        "package_revise",
        match={"id": dataset["id"]},
        update__resources__0={"name": "new name"},
    )
    assert response["package"]["resources"][0]["name"] == "new name"


@pytest.mark.usefixtures("non_clean_db")
def test_revise_resource_by_id():
    _id = str(uuid.uuid4())
    dataset = factories.Dataset(
        resources=[
            {
                "id": _id,
                "url": "http://example.com",
                "name": "old name",
            }
        ]
    )
    params = {
        "match": {"id": dataset["id"]},
        f"update__resources__{_id[:5]}": {
            "name": "new name"
        },  # prefixes allowed >4 chars
    }
    response = helpers.call_action("package_revise", **params)
    assert response["package"]["resources"][0]["name"] == "new name"


@pytest.mark.usefixtures("non_clean_db")
def test_revise_resource_replace_all():

    _id = str(uuid.uuid4())
    dataset = factories.Dataset(
        resources=[
            {
                "id": _id,
                "url": "http://example.com",
                "name": "old name",
            }
        ]
    )
    prefix = _id[:5]
    params = {
        "match": {"id": dataset["id"]},
        "filter": [f"+resources__{prefix}__id", f"-resources__{prefix}__*"],
        f"update__resources__{prefix}": {"name": "new name"},
    }
    response = helpers.call_action("package_revise", **params)
    assert response["package"]["resources"][0]["name"] == "new name"
    assert response["package"]["resources"][0]["url"] == ""


@pytest.mark.usefixtures("non_clean_db")
def test_revise_normal_user():
    user = factories.User()
    org = factories.Organization(users=[{"name": user["id"], "capacity": "admin"}])
    # make sure normal users can use package_revise
    context = {"user": user["name"], "ignore_auth": False}
    ds = factories.Dataset(owner_org=org["id"])
    response = helpers.call_action(
        "package_revise",
        match={"id": ds["id"]},
        update={"notes": "new notes"},
        context=context,
    )
    assert response["package"]["notes"] == "new notes"


@pytest.mark.usefixtures("non_clean_db")
def test_package_revise_resource_copies_other_resources():
    from ckan.lib.dictization import model_save

    res1 = factories.Resource()
    factories.Resource(
        package_id=res1["package_id"],
        url="http://data",
    )
    params = {
        "match": {"id": res1["package_id"]},
        "update__resources__1": {"url": "http://data2"},
    }
    with mock.patch(
        "ckan.lib.dictization.model_save.package_dict_save",
        wraps=model_save.package_dict_save,
    ) as m:
        helpers.call_action("package_revise", **params)
        assert m.call_args.args[3] == {0: 0}, "res 0 unmodified"


@pytest.mark.usefixtures("clean_db")
def test_stored_on_update_if_sysadmin():
    sysadmin = factories.Sysadmin()

    dataset = factories.Dataset(plugin_data={"plugin1": {"key1": "value1"}})
    context = {
        "user": sysadmin["name"],
        "ignore_auth": False,
        "auth_user_obj": model.User.get(sysadmin["name"]),
    }

    pkg_dict = {
        "id": dataset["id"],
        "plugin_data": {"plugin1": {"key1": "updated_value", "key2": "value2"}},
    }
    helpers.call_action("package_update", context=context, **pkg_dict)

    pkg_dict = helpers.call_action(
        "package_show", context=context, id=dataset["id"], include_plugin_data=True
    )
    assert pkg_dict["plugin_data"] == {
        "plugin1": {"key1": "updated_value", "key2": "value2"}
    }

    plugin_data_from_db = model.Session.execute(
        sa.text('SELECT plugin_data from "package" where id=:id'), {"id": dataset["id"]}
    ).first()

    assert plugin_data_from_db[0] == {
        "plugin1": {"key1": "updated_value", "key2": "value2"}
    }


@pytest.mark.usefixtures("clean_db")
def test_ignored_on_update_if_non_sysadmin():
    user = factories.User()
    dataset = factories.Dataset(plugin_data={"plugin1": {"key1": "value1"}})
    context = {
        "user": user["name"],
        "ignore_auth": False,
    }
    pkg_dict = {
        "id": dataset["id"],
        "plugin_data": {"plugin1": {"key1": "updated_value", "key2": "value2"}},
    }
    updated_pkg = helpers.call_action("package_update", context=context, **pkg_dict)

    assert "plugin_data" not in updated_pkg
    pkg = model.Package.get(dataset["id"])
    assert pkg.plugin_data == {"plugin1": {"key1": "value1"}}
