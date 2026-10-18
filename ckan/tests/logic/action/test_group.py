"""Tests for actions and authorization in ckan/logic/action/group.py."""

import re
import uuid

import pytest

import ckan.logic as logic
import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers


@pytest.mark.usefixtures("non_clean_db")
def test_group_member_creation():
    user = factories.User()
    group = factories.Group()

    new_membership = helpers.call_action(
        "group_member_create",
        id=group["id"],
        username=user["name"],
        role="member",
    )

    assert new_membership["group_id"] == group["id"]
    assert new_membership["table_name"] == "user"
    assert new_membership["table_id"] == user["id"]
    assert new_membership["capacity"] == "member"


@pytest.mark.usefixtures("non_clean_db")
def test_organization_member_creation():
    user = factories.User()
    organization = factories.Organization()

    new_membership = helpers.call_action(
        "organization_member_create",
        id=organization["id"],
        username=user["name"],
        role="member",
    )

    assert new_membership["group_id"] == organization["id"]
    assert new_membership["table_name"] == "user"
    assert new_membership["table_id"] == user["id"]
    assert new_membership["capacity"] == "member"


@pytest.mark.usefixtures("non_clean_db")
def test_group_member_creation_raises_validation_error_if_id_missing():

    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "group_member_create",
            username=factories.User.stub().name,
            role="member",
        )


@pytest.mark.usefixtures("non_clean_db")
def test_group_member_creation_raises_validation_error_if_username_missing():

    with pytest.raises(logic.ValidationError):
        helpers.call_action("group_member_create", id="someid", role="member")


@pytest.mark.usefixtures("non_clean_db")
def test_group_member_creation_raises_validation_error_if_role_missing(faker):

    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "group_member_create",
            id=faker.uuid4(),
            username=factories.User.stub().name,
        )


@pytest.mark.usefixtures("non_clean_db")
def test_org_member_creation_raises_validation_error_if_id_missing():

    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "organization_member_create",
            username=factories.User.stub().name,
            role="member",
        )


@pytest.mark.usefixtures("non_clean_db")
def test_org_member_creation_raises_validation_error_if_username_missing():

    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "organization_member_create",
            id=factories.Group.stub().name,
            role="member",
        )


@pytest.mark.usefixtures("non_clean_db")
def test_org_member_creation_raises_validation_error_if_role_missing(faker):

    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "organization_member_create",
            id=faker.uuid4(),
            username=factories.User.stub().name,
        )


@pytest.mark.usefixtures("non_clean_db")
def test_create_group():
    user = factories.User()
    context = {"user": user["name"], "ignore_auth": True}

    group = helpers.call_action(
        "group_create", context=context, name=factories.Group.stub().name
    )

    assert group["display_name"] == group["name"]
    assert group["package_count"] == 0
    assert not group["is_organization"]
    assert group["type"] == "group"
    group_users = helpers.call_action(
        "group_show",
        context=context,
        id=group["id"],
        include_users=True,
    )
    assert group_users["users"] == [
        {
            "capacity": "admin",
            **{k: v for k, v in user.items() if k not in ("apikey", "email")},
        }
    ]


@pytest.mark.usefixtures("non_clean_db")
def test_create_group_validation_fail():
    user = factories.User()
    context = {"user": user["name"], "ignore_auth": True}

    with pytest.raises(logic.ValidationError):
        helpers.call_action("group_create", context=context, name="")


@pytest.mark.usefixtures("non_clean_db")
def test_create_group_return_id():

    user = factories.User()
    context = {
        "user": user["name"],
        "ignore_auth": True,
        "return_id_only": True,
    }

    group = helpers.call_action(
        "group_create", context=context, name=factories.Group.stub().name
    )

    assert isinstance(group, str)
    assert re.match(r"([a-f\d]{8}(-[a-f\d]{4}){3}-[a-f\d]{12}?)", group)


@pytest.mark.usefixtures("non_clean_db")
def test_create_matches_show():
    user = factories.User()
    context = {"user": user["name"], "ignore_auth": True}

    created = helpers.call_action(
        "organization_create",
        context=context,
        name=factories.Organization.stub().name,
    )

    shown = helpers.call_action(
        "organization_show", context=context, id=created["name"]
    )

    assert sorted(created.keys()) == sorted(shown.keys())
    for k in created.keys():
        assert created[k] == shown[k], k


@pytest.mark.usefixtures("non_clean_db")
def test_normal_user_cant_set_id():
    user = factories.User()
    context = {"user": user["name"], "ignore_auth": False}
    _id = str(uuid.uuid4())
    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "group_create", context=context, name=f"test-group-{_id}", id=_id
        )


@pytest.mark.usefixtures("non_clean_db")
def test_sysadmin_can_set_id():
    user = factories.Sysadmin()
    context = {"user": user["name"], "ignore_auth": False}
    _id = str(uuid.uuid4())
    result = helpers.call_action(
        "group_create", context=context, name=f"test-group-{_id}", id=_id
    )
    assert result.get("id") == _id


@pytest.mark.usefixtures("non_clean_db")
def test_id_cant_already_exist():
    user = factories.Sysadmin()
    context = {"user": user["name"], "ignore_auth": False}
    group = helpers.call_action(
        "group_create", name=factories.Group.stub().name, context=context
    )
    with pytest.raises(logic.ValidationError) as exception:
        helpers.call_action(
            "group_create",
            id=group["id"],
            context=context,
            name=factories.Group.stub().name,
        )
    assert "Id already exists" in str(exception.value)


@pytest.mark.usefixtures("non_clean_db")
def test_normal_user_cant_set_extras_id():
    user = factories.User()
    context = {"user": user["name"], "ignore_auth": False}
    _id = str(uuid.uuid4())
    with pytest.raises(logic.ValidationError) as exception:
        helpers.call_action(
            "group_create",
            context=context,
            name=f"test-group-{_id}",
            extras=[{"id": _id, "key": "area", "value": '"non profit"'}],
        )
    assert "The input field id was not expected" in str(exception.value)


@pytest.mark.usefixtures("non_clean_db")
def test_sysadmin_user_cant_set_extras_id():
    user = factories.Sysadmin()
    context = {"user": user["name"], "ignore_auth": False}
    _id = str(uuid.uuid4())
    helpers.call_action(
        "group_create",
        context=context,
        name=f"test-group-{_id}",
        extras=[{"id": _id, "key": "area", "value": '"non profit"'}],
    )


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.usefixtures("clean_index")
def test_member_create_reindexes_package_groups():
    group = factories.Group()
    package = factories.Dataset()

    def get_search_result_groups():
        results = helpers.call_action("package_search", q=package["title"])["results"]
        return [group["name"] for group in results[0]["groups"]]

    assert get_search_result_groups() == []

    helpers.call_action(
        "member_create",
        object=package["id"],
        id=group["id"],
        object_type="package",
        capacity="public",
    )

    assert get_search_result_groups() == [group["name"]]


@pytest.mark.usefixtures("non_clean_db")
def test_member_create_accepts_object_name_or_id():
    org = factories.Organization()
    package = factories.Dataset()
    helpers.call_action(
        "member_create",
        object=package["id"],
        id=org["id"],
        object_type="package",
        capacity="member",
    )
    helpers.call_action(
        "member_create",
        object=package["name"],
        id=org["id"],
        object_type="package",
        capacity="member",
    )


@pytest.mark.usefixtures("non_clean_db")
def test_member_create_raises_if_user_unauthorized_to_update_group():
    org = factories.Organization()
    pkg = factories.Dataset()
    user = factories.User()
    context = {"ignore_auth": False, "user": user["name"]}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_action(
            "member_create",
            context,
            object=pkg["name"],
            id=org["id"],
            object_type="package",
            capacity="member",
        )


@pytest.mark.usefixtures("non_clean_db")
def test_member_create_raises_if_any_required_parameter_isnt_defined():
    org = factories.Organization()
    pkg = factories.Dataset()
    data = dict(
        object=pkg["name"],
        id=org["id"],
        object_type="package",
        capacity="member",
    )
    for key in ["id", "object", "object_type"]:
        payload = data.copy()
        payload.pop(key)
        with pytest.raises(logic.ValidationError):
            helpers.call_action("member_create", **payload)


@pytest.mark.usefixtures("non_clean_db")
def test_member_create_raises_if_group_wasnt_found():
    pkg = factories.Dataset()
    with pytest.raises(logic.NotFound):
        helpers.call_action(
            "member_create",
            object=pkg["name"],
            id="not-real",
            object_type="package",
            capacity="member",
        )


@pytest.mark.usefixtures("non_clean_db")
def test_member_create_raises_if_object_wasnt_found():
    org = factories.Organization()
    with pytest.raises(logic.NotFound):
        helpers.call_action(
            "member_create",
            object="not-real",
            id=org["id"],
            object_type="package",
            capacity="member",
        )


@pytest.mark.usefixtures("non_clean_db")
def test_member_create_raises_if_object_type_is_invalid():
    org = factories.Organization()
    pkg = factories.Dataset()
    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "member_create",
            object=pkg["name"],
            id=org["id"],
            object_type="notvalid",
            capacity="member",
        )


@pytest.mark.usefixtures("non_clean_db")
def test_a_non_sysadmin_cant_purge_group():
    user = factories.User()
    group = factories.Group(user=user)

    with pytest.raises(logic.NotAuthorized):
        helpers.call_action(
            "group_purge",
            context={"user": user["name"], "ignore_auth": False},
            id=group["name"],
        )


@pytest.mark.usefixtures("non_clean_db")
def test_purged_group_does_not_show():
    group = factories.Group()

    helpers.call_action("group_purge", id=group["name"])

    with pytest.raises(logic.NotFound):
        helpers.call_action("group_show", context={}, id=group["name"])


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.usefixtures("clean_db")
def test_purged_group_is_not_listed():
    group = factories.Group()

    helpers.call_action("group_purge", id=group["name"])

    assert helpers.call_action("group_list", context={}) == []


@pytest.mark.usefixtures("non_clean_db")
def test_dataset_in_a_purged_group_no_longer_shows_that_group():
    group = factories.Group()
    dataset = factories.Dataset(groups=[{"name": group["name"]}])

    helpers.call_action("group_purge", id=group["name"])

    dataset_shown = helpers.call_action("package_show", context={}, id=dataset["id"])
    assert dataset_shown["groups"] == []


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.usefixtures("clean_index")
def test_purged_group_is_not_in_search_results_for_its_ex_dataset():
    group = factories.Group()
    dataset = factories.Dataset(groups=[{"name": group["name"]}])

    def get_search_result_groups():
        results = helpers.call_action("package_search", q=dataset["title"])["results"]
        return [g["name"] for g in results[0]["groups"]]

    assert get_search_result_groups() == [group["name"]]

    helpers.call_action("group_purge", id=group["name"])

    assert get_search_result_groups() == []


@pytest.mark.usefixtures("non_clean_db")
def test_purged_group_leaves_no_trace_in_the_model():
    parent = factories.Group()
    user = factories.User()
    group1 = factories.Group(
        extras=[{"key": "key1", "value": "val1"}],
        users=[{"name": user["name"]}],
        groups=[{"name": parent["name"]}],
    )
    ds = factories.Dataset(groups=[{"name": group1["name"]}])
    child = factories.Group(groups=[{"name": group1["name"]}])

    helpers.call_action("group_purge", id=group1["name"])

    assert not model.Group.get(group1["name"])
    # the only members left are the users for the parent and child
    assert sorted(
        (m.table_name, m.group.name)
        for m in model.Session.query(model.Member)
        .join(model.Group)
        .filter(model.Group.id.in_([parent["id"], child["id"], group1["id"]]))
    ) == sorted([("user", child["name"]), ("user", parent["name"])])
    # the dataset is still there though
    assert model.Package.get(ds["name"])


@pytest.mark.usefixtures("non_clean_db")
def test_missing_id_returns_error():
    with pytest.raises(logic.ValidationError):
        helpers.call_action("group_purge")


@pytest.mark.usefixtures("non_clean_db")
def test_bad_id_returns_404():
    with pytest.raises(logic.NotFound):
        helpers.call_action("group_purge", id="123")


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.usefixtures("clean_index")
def test_member_delete_reindexes_package_groups():
    group = factories.Group()
    package = factories.Dataset(groups=[{"id": group["id"]}])

    def get_search_result_groups():
        results = helpers.call_action("package_search", q=package["title"])["results"]
        return [group["name"] for group in results[0]["groups"]]

    assert get_search_result_groups() == [group["name"]]

    helpers.call_action(
        "member_delete",
        object=package["id"],
        id=group["id"],
        object_type="package",
    )

    assert get_search_result_groups() == []


@pytest.mark.usefixtures("non_clean_db")
def test_member_delete_accepts_object_name_or_id():
    org = factories.Organization()
    user = factories.User()
    helpers.call_action(
        "member_delete",
        object=user["id"],
        id=org["id"],
        object_type="user",
        capacity="member",
    )
    helpers.call_action(
        "member_create",
        object=user["name"],
        id=org["id"],
        object_type="user",
        capacity="member",
    )


@pytest.mark.usefixtures("non_clean_db")
def test_member_delete_raises_if_user_unauthorized_to_update_group():
    org = factories.Organization()
    pkg = factories.Dataset()
    user = factories.User()
    context = {"ignore_auth": False, "user": user["name"]}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_action(
            "member_delete",
            context,
            object=pkg["name"],
            id=org["id"],
            object_type="package",
            capacity="member",
        )


@pytest.mark.usefixtures("non_clean_db")
def test_member_delete_raises_if_any_required_parameter_isnt_defined():
    org = factories.Organization()
    pkg = factories.Dataset()
    data = dict(
        object=pkg["name"],
        id=org["id"],
        object_type="package",
        capacity="member",
    )
    for key in ["id", "object", "object_type"]:
        payload = data.copy()
        payload.pop(key)
        with pytest.raises(logic.ValidationError):
            helpers.call_action("member_delete", **payload)


@pytest.mark.usefixtures("non_clean_db")
def test_member_delete_raises_if_group_wasnt_found():
    pkg = factories.Dataset()
    with pytest.raises(logic.NotFound):
        helpers.call_action(
            "member_delete",
            object=pkg["name"],
            id="not-real",
            object_type="package",
            capacity="member",
        )


@pytest.mark.usefixtures("non_clean_db")
def test_member_delete_raises_if_object_wasnt_found():
    org = factories.Organization()
    with pytest.raises(logic.NotFound):
        helpers.call_action(
            "member_delete",
            object="not-real",
            id=org["id"],
            object_type="package",
            capacity="member",
        )


@pytest.mark.usefixtures("non_clean_db")
def test_member_delete_raises_if_object_type_is_invalid():
    org = factories.Organization()
    pkg = factories.Dataset()
    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "member_delete",
            object=pkg["name"],
            id=org["id"],
            object_type="notvalid",
            capacity="member",
        )


@pytest.mark.usefixtures("clean_db")
class TestGroupList(object):
    def test_group_list(self):

        group1 = factories.Group()
        group2 = factories.Group()

        group_list = helpers.call_action("group_list")

        assert sorted(group_list) == sorted([g["name"] for g in [group1, group2]])

    def test_group_list_in_presence_of_organizations(self):
        """
        Getting the group_list should only return groups of type 'group' (not
        organizations).
        """
        group1 = factories.Group()
        group2 = factories.Group()
        factories.Organization()
        factories.Organization()

        group_list = helpers.call_action("group_list")

        assert sorted(group_list) == sorted([g["name"] for g in [group1, group2]])

    def test_group_list_in_presence_of_custom_group_types(self):
        """Getting the group_list shouldn't return custom group types."""
        group1 = factories.Group()
        group2 = factories.Group()
        factories.Group(type="custom")

        group_list = helpers.call_action("group_list")

        assert sorted(group_list) == sorted([g["name"] for g in [group1, group2]])

    def test_group_list_return_custom_group(self):
        """
        Getting the group_list with a type defined should only return
        groups of that type.
        """
        group1 = factories.Group(type="custom")
        group2 = factories.Group(type="custom")
        factories.Group()
        factories.Group()

        group_list = helpers.call_action("group_list", type="custom")

        assert sorted(group_list) == sorted([g["name"] for g in [group1, group2]])

    def test_group_list_sort_by_package_count(self):

        factories.Group(name="aa")
        factories.Group(name="bb")
        factories.Dataset(groups=[{"name": "aa"}, {"name": "bb"}])
        factories.Dataset(groups=[{"name": "bb"}])

        group_list = helpers.call_action("group_list", sort="package_count")
        assert sorted(group_list) == sorted(["bb", "aa"])

    def test_group_list_sort_by_package_count_ascending(self):

        factories.Group(name="aa")
        factories.Group(name="bb")
        factories.Dataset(groups=[{"name": "aa"}, {"name": "bb"}])
        factories.Dataset(groups=[{"name": "aa"}])

        group_list = helpers.call_action("group_list", sort="package_count asc")

        assert group_list == ["bb", "aa"]

    def test_group_list_sort_default(self):

        factories.Group(name="zz", title="aa")
        factories.Group(name="yy", title="bb")

        group_list = helpers.call_action("group_list")

        assert group_list == ["zz", "yy"]

    @pytest.mark.ckan_config("ckan.default_group_sort", "name")
    def test_group_list_sort_from_config(self):

        factories.Group(name="zz", title="aa")
        factories.Group(name="yy", title="bb")

        group_list = helpers.call_action("group_list")

        assert group_list == ["yy", "zz"]

    def eq_expected(self, expected_dict, result_dict):
        superfluous_keys = set(result_dict) - set(expected_dict)
        assert not superfluous_keys, "Did not expect key: %s" % " ".join(
            ("%s=%s" % (k, result_dict[k]) for k in superfluous_keys)
        )
        for key in expected_dict:
            assert expected_dict[key] == result_dict[key], "%s=%s should be %s" % (
                key,
                result_dict[key],
                expected_dict[key],
            )

    def test_group_list_all_fields(self):

        group = factories.Group()

        group_list = helpers.call_action("group_list", all_fields=True)

        expected_group = dict(group)
        del expected_group["extras"]
        del expected_group["groups"]

        assert group_list[0] == expected_group
        assert "extras" not in group_list[0]
        assert "tags" not in group_list[0]
        assert "groups" not in group_list[0]
        assert "users" not in group_list[0]
        assert "datasets" not in group_list[0]

    def _create_bulk_groups(self, name, count):

        groups = [model.Group(name="{}_{}".format(name, i)) for i in range(count)]
        model.Session.add_all(groups)
        model.repo.commit_and_remove()

    def test_limit_default(self):
        self._create_bulk_groups("group_default", 1010)
        results = helpers.call_action("group_list")
        assert len(results) == 1000  # i.e. default value

    @pytest.mark.ckan_config("ckan.group_and_organization_list_max", "5")
    def test_limit_configured(self):
        self._create_bulk_groups("group_default", 7)
        results = helpers.call_action("group_list")
        assert len(results) == 5  # i.e. configured limit

    def test_all_fields_limit_default(self):
        self._create_bulk_groups("org_all_fields_default", 30)
        results = helpers.call_action("group_list", all_fields=True)
        assert len(results) == 25  # i.e. default value

    @pytest.mark.ckan_config("ckan.group_and_organization_list_all_fields_max", "5")
    def test_all_fields_limit_configured(self):
        self._create_bulk_groups("org_all_fields_default", 30)
        results = helpers.call_action("group_list", all_fields=True)
        assert len(results) == 5  # i.e. configured limit

    def test_group_list_extras_returned(self):

        group = factories.Group(extras=[{"key": "key1", "value": "val1"}])

        group_list = helpers.call_action(
            "group_list", all_fields=True, include_extras=True
        )

        assert group_list[0]["extras"] == group["extras"]
        assert group_list[0]["extras"][0]["key"] == "key1"

    def test_group_list_users_returned(self):
        user = factories.User()
        group = factories.Group(users=[{"name": user["name"], "capacity": "admin"}])

        group_list = helpers.call_action(
            "group_list", all_fields=True, include_users=True
        )

        assert group_list[0]["users"] == group["users"]
        assert group_list[0]["users"][0]["name"] == group["users"][0]["name"]

    # NB there is no test_group_list_tags_returned because tags are not in the
    # group_create schema (yet)

    def test_group_list_groups_returned(self):

        parent_group = factories.Group(tags=[{"name": "river"}])
        child_group = factories.Group(
            groups=[{"name": parent_group["name"]}], tags=[{"name": "river"}]
        )

        group_list = helpers.call_action(
            "group_list", all_fields=True, include_groups=True
        )

        child_group_returned = group_list[0]
        if group_list[0]["name"] == child_group["name"]:
            child_group_returned, _ = group_list
        else:
            child_group_returned, _ = group_list[::-1]
        expected_parent_group = dict(parent_group)

        assert [g["name"] for g in child_group_returned["groups"]] == [
            expected_parent_group["name"]
        ]

    def test_group_list_limit(self):

        group1 = factories.Group(title="aa")
        group2 = factories.Group(title="bb")
        group3 = factories.Group(title="cc")
        group_names = [g["name"] for g in [group1, group2, group3]]

        group_list = helpers.call_action("group_list", limit=1)

        assert len(group_list) == 1
        assert group_list[0] == group_names[0]

    def test_group_list_offset(self):

        group1 = factories.Group(title="aa")
        group2 = factories.Group(title="bb")
        group3 = factories.Group(title="cc")
        group_names = [g["name"] for g in [group1, group2, group3]]

        group_list = helpers.call_action("group_list", offset=2)

        assert len(group_list) == 1
        # group list returns sorted result. This is not necessarily
        # order of creation
        assert group_list[0] == group_names[2]

    def test_group_list_limit_and_offset(self):

        factories.Group(title="aa")
        group2 = factories.Group(title="bb")
        factories.Group(title="cc")

        group_list = helpers.call_action("group_list", offset=1, limit=1)

        assert len(group_list) == 1
        assert group_list[0] == group2["name"]

    def test_group_list_limit_as_string(self):

        factories.Group(name="aa")
        factories.Group(name="bb")

        group_list = helpers.call_action("group_list", limit="1")

        assert len(group_list) == 1

    def test_group_list_wrong_limit(self):

        with pytest.raises(logic.ValidationError):
            helpers.call_action("group_list", limit="a")

    def test_group_list_wrong_offset(self):

        with pytest.raises(logic.ValidationError):
            helpers.call_action("group_list", offset="-2")

    @pytest.mark.parametrize("value", ["bb,cc", ["bb", "cc"]])
    def test_group_list_filter_by_name(self, value):

        factories.Group(name="aa")
        factories.Group(name="bb")
        factories.Group(name="cc")

        group_list = helpers.call_action("group_list", groups=value, sort="name asc")

        assert len(group_list) == 2
        assert group_list[0] == "bb"
        assert group_list[1] == "cc"


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_group_show():
    group = factories.Group(user=factories.User())

    group_dict = helpers.call_action(
        "group_show", id=group["id"], include_datasets=True
    )

    group_dict.pop("packages", None)
    assert group_dict == group


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_group_show_error_not_found():

    with pytest.raises(logic.NotFound):
        helpers.call_action("group_show", id="does_not_exist")


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_group_show_error_for_organization():

    org = factories.Organization()

    with pytest.raises(logic.NotFound):
        helpers.call_action("group_show", id=org["id"])


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_group_show_packages_returned():
    user_name = helpers.call_action("get_site_user")["name"]

    group = factories.Group(user=factories.User())

    datasets = [
        {"name": "dataset_1", "groups": [{"name": group["name"]}]},
        {"name": "dataset_2", "groups": [{"name": group["name"]}]},
    ]

    for dataset in datasets:
        helpers.call_action("package_create", context={"user": user_name}, **dataset)

    group_dict = helpers.call_action(
        "group_show", id=group["id"], include_datasets=True
    )

    assert len(group_dict["packages"]) == 2
    assert group_dict["package_count"] == 2


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_group_show_packages_returned_for_view():

    user_name = helpers.call_action("get_site_user")["name"]

    group = factories.Group(user=factories.User())

    datasets = [
        {"name": "dataset_1", "groups": [{"name": group["name"]}]},
        {"name": "dataset_2", "groups": [{"name": group["name"]}]},
    ]

    for dataset in datasets:
        helpers.call_action("package_create", context={"user": user_name}, **dataset)

    group_dict = helpers.call_action(
        "group_show",
        id=group["id"],
        include_datasets=True,
        context={"for_view": True},
    )

    assert len(group_dict["packages"]) == 2
    assert group_dict["package_count"] == 2


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_group_show_no_packages_returned():

    user_name = helpers.call_action("get_site_user")["name"]

    group = factories.Group(user=factories.User())

    datasets = [
        {"name": "dataset_1", "groups": [{"name": group["name"]}]},
        {"name": "dataset_2", "groups": [{"name": group["name"]}]},
    ]

    for dataset in datasets:
        helpers.call_action("package_create", context={"user": user_name}, **dataset)

    group_dict = helpers.call_action(
        "group_show", id=group["id"], include_datasets=False
    )

    assert "packages" not in group_dict
    assert group_dict["package_count"] == 2


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_group_show_does_not_show_private_datasets():
    """group_show() should never show private datasets.

    If a dataset is a private member of an organization and also happens to
    be a member of a group, group_show() should not return the dataset as
    part of the group dict, even if the user calling group_show() is a
    member or admin of the group or the organization or is a sysadmin.

    """
    org_member = factories.User()
    org = factories.Organization(user=org_member)
    private_dataset = factories.Dataset(
        user=org_member, owner_org=org["name"], private=True
    )

    group = factories.Group()

    # Add the private dataset to the group.
    helpers.call_action(
        "member_create",
        id=group["id"],
        object=private_dataset["id"],
        object_type="package",
        capacity="public",
    )

    # Create a member user and an admin user of the group.
    group_member = factories.User()
    helpers.call_action(
        "member_create",
        id=group["id"],
        object=group_member["id"],
        object_type="user",
        capacity="member",
    )
    group_admin = factories.User()
    helpers.call_action(
        "member_create",
        id=group["id"],
        object=group_admin["id"],
        object_type="user",
        capacity="admin",
    )

    # Create a user who isn't a member of any group or organization.
    non_member = factories.User()

    sysadmin = factories.Sysadmin()

    # None of the users should see the dataset when they call group_show().
    for user in (
        org_member,
        group_member,
        group_admin,
        non_member,
        sysadmin,
        None,
    ):
        if user is None:
            context = None  # No user logged-in.
        else:
            context = {"user": user["name"]}

        group = helpers.call_action(
            "group_show",
            id=group["id"],
            include_datasets=True,
            context=context,
        )

        assert private_dataset["id"] not in [
            dataset["id"] for dataset in group["packages"]
        ], "group_show() should never show private datasets"


@pytest.mark.usefixtures("clean_db", "clean_index")
@pytest.mark.ckan_config("ckan.search.rows_max", "2")
def test_package_limit_configured():
    group = factories.Group()
    for _ in range(3):
        factories.Dataset(groups=[{"id": group["id"]}])
    id = group["id"]

    results = helpers.call_action("group_show", id=id, include_datasets=1)
    assert len(results["packages"]) == 2  # i.e. ckan.search.rows_max


@pytest.mark.usefixtures("clean_db")
def test_dataset_delete_marks_membership_of_group_as_deleted():
    sysadmin = factories.Sysadmin()
    group = factories.Group()
    dataset = factories.Dataset(groups=[{"name": group["name"]}])
    context = {"user": sysadmin["name"]}

    group_members = helpers.call_action(
        "member_list", context, id=group["id"], object_type="package"
    )

    assert len(group_members) == 1
    assert group_members[0][0] == dataset["id"]
    assert group_members[0][1] == "package"

    helpers.call_action("package_delete", context, id=dataset["id"])

    group_members = helpers.call_action(
        "member_list", context, id=group["id"], object_type="package"
    )

    assert len(group_members) == 0


@pytest.mark.usefixtures("clean_db")
def test_dataset_delete_marks_membership_of_org_as_deleted():
    sysadmin = factories.Sysadmin()
    org = factories.Organization()
    dataset = factories.Dataset(owner_org=org["id"])
    context = {"user": sysadmin["name"]}

    org_members = helpers.call_action(
        "member_list", context, id=org["id"], object_type="package"
    )

    assert len(org_members) == 1
    assert org_members[0][0] == dataset["id"]
    assert org_members[0][1] == "package"

    helpers.call_action("package_delete", context, id=dataset["id"])

    org_members = helpers.call_action(
        "member_list", context, id=org["id"], object_type="package"
    )

    assert len(org_members) == 0


@pytest.mark.usefixtures("clean_db")
def test_user_delete_marks_membership_of_group_as_deleted():
    sysadmin = factories.Sysadmin()
    group = factories.Group()
    user = factories.User()
    context = {"user": sysadmin["name"]}

    member_dict = {
        "username": user["id"],
        "id": group["id"],
        "role": "member",
    }
    helpers.call_action("group_member_create", context, **member_dict)

    group_members = helpers.call_action(
        "member_list",
        context,
        id=group["id"],
        object_type="user",
        capacity="member",
    )

    assert len(group_members) == 1
    assert group_members[0][0] == user["id"]
    assert group_members[0][1] == "user"

    helpers.call_action("user_delete", context, id=user["id"])

    group_members = helpers.call_action(
        "member_list",
        context,
        id=group["id"],
        object_type="user",
        capacity="member",
    )

    assert len(group_members) == 0


@pytest.mark.usefixtures("clean_db")
def test_user_delete_marks_membership_of_org_as_deleted():
    sysadmin = factories.Sysadmin()
    org = factories.Organization()
    user = factories.User()
    context = {"user": sysadmin["name"]}

    member_dict = {
        "username": user["id"],
        "id": org["id"],
        "role": "member",
    }
    helpers.call_action("organization_member_create", context, **member_dict)

    org_members = helpers.call_action(
        "member_list",
        context,
        id=org["id"],
        object_type="user",
        capacity="member",
    )

    assert len(org_members) == 1
    assert org_members[0][0] == user["id"]
    assert org_members[0][1] == "user"

    helpers.call_action("user_delete", context, id=user["id"])

    org_members = helpers.call_action(
        "member_list",
        context,
        id=org["id"],
        object_type="user",
        capacity="member",
    )

    assert len(org_members) == 0


@pytest.mark.usefixtures("clean_db")
def test_user_list_excludes_deleted_users_not_marked_membership_of_org_as_deleted():
    sysadmin = factories.Sysadmin()
    org = factories.Organization()
    user = factories.User()
    context = {"user": sysadmin["name"]}

    member_dict = {
        "username": user["id"],
        "id": org["id"],
        "role": "member",
    }
    helpers.call_action("organization_member_create", context, **member_dict)

    org_members = helpers.call_action(
        "member_list",
        context,
        id=org["id"],
        object_type="user",
        capacity="member",
    )

    assert len(org_members) == 1
    assert org_members[0][0] == user["id"]
    assert org_members[0][1] == "user"

    model.Session.delete(model.User.get(user["id"]))
    model.Session.commit()

    org_members = helpers.call_action(
        "member_list",
        context,
        id=org["id"],
        object_type="user",
        capacity="member",
    )

    assert len(org_members) == 0


@pytest.mark.usefixtures("non_clean_db")
def test_group_package_show():
    group = factories.Group()
    factories.Dataset()
    pkg = factories.Dataset(groups=[{"id": group["id"]}])
    group_packages = helpers.call_action("group_package_show", id=group["id"])
    assert len(group_packages) == 1
    assert group_packages[0]["name"] == pkg["name"]


@pytest.mark.usefixtures("non_clean_db")
def test_group_patch_updating_single_field():
    user = factories.User()
    group = factories.Group(description="some test now", user=user)
    name = group["name"]
    group = helpers.call_action(
        "group_patch",
        id=group["id"],
        description="somethingnew",
        context={"user": user["name"]},
    )

    assert group["name"] == name
    assert group["description"] == "somethingnew"

    group2 = helpers.call_action("group_show", id=group["id"])

    assert group2["name"] == name
    assert group2["description"] == "somethingnew"


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.public_user_details", "false")
def test_group_patch_updating_single_field_when_public_user_details_is_false():
    user = factories.User()
    group = factories.Group(description="some test now", user=user)
    name = group["name"]
    group = helpers.call_action(
        "group_patch",
        id=group["id"],
        description="somethingnew",
        context={"user": user["name"]},
    )

    assert group["name"] == name
    assert group["description"] == "somethingnew"

    group2 = helpers.call_action("group_show", id=group["id"], include_users=True)

    assert group2["name"] == name
    assert group2["description"] == "somethingnew"
    assert len(group2["users"]) == 1
    assert group2["users"][0]["name"] == user["name"]


@pytest.mark.usefixtures("non_clean_db")
def test_group_patch_preserve_datasets():
    user = factories.User()
    group = factories.Group(description="some test now", user=user)
    factories.Dataset(groups=[{"name": group["name"]}])

    group2 = helpers.call_action("group_show", id=group["id"])
    assert 1 == group2["package_count"]

    group = helpers.call_action(
        "group_patch", id=group["id"], context={"user": user["name"]}
    )

    group3 = helpers.call_action("group_show", id=group["id"])
    assert 1 == group3["package_count"]

    group = helpers.call_action(
        "group_patch",
        id=group["id"],
        packages=[],
        context={"user": user["name"]},
    )

    group4 = helpers.call_action("group_show", id=group["id"], include_datasets=True)
    assert 0 == group4["package_count"]


@pytest.mark.usefixtures("non_clean_db")
def test_group_update_image_url_field():
    user = factories.User()
    context = {"user": user["name"]}
    group = factories.Group(
        type="group",
        user=user,
        image_url="group_image.jpg",
    )

    group = helpers.call_action(
        "group_update",
        context=context,
        id=group["id"],
        name=group["name"],
        type=group["type"],
        image_url="new_image_url.jpg",
    )

    assert group["image_url"] == "new_image_url.jpg"


@pytest.mark.usefixtures("non_clean_db")
def test_group_update_locates_group_by_name(group, faker):
    description = faker.sentence()
    original_id = group["id"]
    group = helpers.call_action(
        "group_update", id=group["name"], description=description
    )

    assert group["id"] == original_id
    assert group["description"] == description


@pytest.mark.usefixtures("non_clean_db")
def test_group_update_cant_change_type():
    user = factories.User()
    context = {"user": user["name"]}
    group = factories.Group(type="group", user=user)

    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "group_update",
            context=context,
            name=group["name"],
            id=group["id"],
            type="favouritecolour",
        )


@pytest.mark.usefixtures("non_clean_db")
def test_extras_removed_if_missing():
    group = factories.Group(extras=[{"key": "e", "value": "v"}])
    assert group["extras"] == [{"key": "e", "value": "v"}]
    updated_group = helpers.call_action(
        "group_update",
        id=group["name"],
    )

    assert updated_group["extras"] == []


@pytest.mark.usefixtures("non_clean_db")
def test_groups_unchanged_if_missing():
    group1 = factories.Group()
    group2 = factories.Group(groups=[{"name": group1["name"]}])
    assert group2["groups"][0]["name"] == group1["name"]
    updated_group = helpers.call_action(
        "group_update",
        id=group2["name"],
    )

    assert updated_group["groups"][0]["name"] == group1["name"]


@pytest.mark.usefixtures("non_clean_db")
def test_groups_removed_if_empty_list():
    group1 = factories.Group()
    group2 = factories.Group(groups=[{"name": group1["name"]}])
    assert group2["groups"][0]["name"] == group1["name"]
    updated_group = helpers.call_action(
        "group_update",
        id=group2["name"],
        groups=[],
    )

    assert updated_group["groups"] == []


@pytest.mark.usefixtures("non_clean_db")
def test_users_unchanged_if_missing():
    user = factories.User()
    group = factories.Group(users=[user])
    assert user["name"] in (g["name"] for g in group["users"])
    updated_group = helpers.call_action(
        "group_update",
        id=group["name"],
    )

    assert user["name"] in (g["name"] for g in updated_group["users"])


@pytest.mark.usefixtures("non_clean_db")
def test_users_removed_if_empty_list():
    user = factories.User()
    group = factories.Group(users=[user])
    assert user["name"] in (g["name"] for g in group["users"])
    updated_group = helpers.call_action("group_update", id=group["name"], users=[])

    assert updated_group["users"] == []
