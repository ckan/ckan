"""Tests for actions and authorization in ckan/logic/action/organization.py."""

import re
import uuid

import pytest

from ckan import logic, model
from ckan.tests import factories, helpers


@pytest.mark.usefixtures("non_clean_db")
def test_create_organization():
    user = factories.User()
    context = {"user": user["name"], "ignore_auth": True}

    org = helpers.call_action(
        "organization_create",
        context=context,
        name=factories.Organization.stub().name,
    )

    assert org["display_name"] == org["name"]
    assert org["package_count"] == 0
    assert org["is_organization"]
    assert org["type"] == "organization"
    org_users = helpers.call_action(
        "organization_show",
        context=context,
        id=org["id"],
        include_users=True,
    )
    assert org_users["users"] == [
        {
            "capacity": "admin",
            **{k: v for k, v in user.items() if k not in ("apikey", "email")},
        }
    ]


@pytest.mark.usefixtures("non_clean_db")
def test_create_organization_validation_fail():
    user = factories.User()
    context = {"user": user["name"], "ignore_auth": True}

    with pytest.raises(logic.ValidationError):
        helpers.call_action("organization_create", context=context, name="")


@pytest.mark.usefixtures("non_clean_db")
def test_create_organization_return_id():

    user = factories.User()
    context = {
        "user": user["name"],
        "ignore_auth": True,
        "return_id_only": True,
    }

    org = helpers.call_action(
        "organization_create",
        context=context,
        name=factories.Organization.stub().name,
    )

    assert isinstance(org, str)
    assert re.match(r"([a-f\d]{8}(-[a-f\d]{4}){3}-[a-f\d]{12}?)", org)


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
def test_create_organization_custom_type():
    custom_org_type = "some-custom-type"
    user = factories.User()
    context = {"user": user["name"], "ignore_auth": True}

    org = helpers.call_action(
        "organization_create",
        context=context,
        name=factories.Organization.stub().name,
        type=custom_org_type,
    )

    assert org["display_name"] == org["name"]
    assert org["package_count"] == 0
    assert org["is_organization"]
    assert org["type"] == custom_org_type


@pytest.mark.usefixtures("non_clean_db")
def test_normal_user_cant_set_id():
    user = factories.User()
    context = {"user": user["name"], "ignore_auth": False}
    _id = str(uuid.uuid4())
    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "organization_create", context=context, name=f"test-org-{_id}", id=_id
        )


@pytest.mark.usefixtures("non_clean_db")
def test_sysadmin_can_set_id():
    user = factories.Sysadmin()
    context = {"user": user["name"], "ignore_auth": False}
    _id = str(uuid.uuid4())
    result = helpers.call_action(
        "organization_create", context=context, name=f"test-org-{_id}", id=_id
    )
    assert result.get("id") == _id


@pytest.mark.usefixtures("non_clean_db")
def test_id_cant_already_exist():
    user = factories.Sysadmin()
    context = {"user": user["name"], "ignore_auth": False}
    group = factories.Group()
    with pytest.raises(logic.ValidationError) as exception:
        helpers.call_action(
            "group_create", id=group.pop("id"), context=context, name=group.pop("name")
        )
    assert "Id already exists" in str(exception.value)


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.create_unowned_dataset", False)
def test_delete_org_without_datasets():
    user = factories.User()
    org = factories.Organization(user=user)

    helpers.call_action(
        "organization_delete",
        context={"user": user["name"]},
        id=org["name"],
    )

    assert model.Group.get(org["id"]).state == "deleted"


@pytest.mark.usefixtures("non_clean_db")
def test_a_non_sysadmin_cant_purge_org():
    user = factories.User()
    org = factories.Organization(user=user)

    with pytest.raises(logic.NotAuthorized):
        helpers.call_action(
            "organization_purge",
            context={"user": user["name"], "ignore_auth": False},
            id=org["name"],
        )


@pytest.mark.usefixtures("non_clean_db")
def test_purged_org_does_not_show():
    org = factories.Organization()

    helpers.call_action("organization_purge", id=org["name"])

    with pytest.raises(logic.NotFound):
        helpers.call_action("organization_show", context={}, id=org["name"])


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.usefixtures("clean_db")
def test_purged_org_is_not_listed():
    org = factories.Organization()

    helpers.call_action("organization_purge", id=org["name"])

    assert helpers.call_action("organization_list", context={}) == []


@pytest.mark.usefixtures("non_clean_db")
def test_dataset_in_a_purged_org_no_longer_shows_that_org():
    org = factories.Organization()
    dataset = factories.Dataset(owner_org=org["id"])

    helpers.call_action("organization_purge", id=org["name"])

    dataset_shown = helpers.call_action("package_show", context={}, id=dataset["id"])
    assert dataset_shown["owner_org"] is None


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.usefixtures("clean_index")
def test_purged_org_is_not_in_search_results_for_its_ex_dataset():
    org = factories.Organization()
    dataset = factories.Dataset(owner_org=org["id"])

    def get_search_result_owner_org():
        results = helpers.call_action("package_search", q=dataset["title"])["results"]
        return results[0]["owner_org"]

    assert get_search_result_owner_org() == org["id"]

    helpers.call_action("organization_purge", id=org["name"])

    assert get_search_result_owner_org() is None


@pytest.mark.usefixtures("non_clean_db")
def test_purged_organization_leaves_no_trace_in_the_model():
    parent = factories.Organization()
    user = factories.User()
    org1 = factories.Organization(
        extras=[{"key": "key1", "value": "val1"}],
        users=[{"name": user["name"]}],
        groups=[{"name": parent["name"]}],
    )
    ds = factories.Dataset(owner_org=org1["id"])
    child = factories.Organization(groups=[{"name": org1["name"]}])

    helpers.call_action("organization_purge", id=org1["name"])

    assert not model.Group.get(org1["id"])
    # the only members left are the users for the parent and child
    assert sorted(
        (m.table_name, m.group.name)
        for m in model.Session.query(model.Member)
        .join(model.Group)
        .filter(model.Group.id.in_([parent["id"], child["id"], org1["id"]]))
    ) == sorted([("user", child["name"]), ("user", parent["name"])])
    # the dataset is still there though
    assert model.Package.get(ds["name"])


@pytest.mark.usefixtures("non_clean_db")
def test_missing_id_returns_error():
    with pytest.raises(logic.ValidationError):
        helpers.call_action("organization_purge")


@pytest.mark.usefixtures("non_clean_db")
def test_bad_id_returns_404():
    with pytest.raises(logic.NotFound):
        helpers.call_action("organization_purge", id="123")


@pytest.mark.usefixtures("clean_db")
class TestOrganizationList(object):
    def test_organization_list(self):

        org1 = factories.Organization()
        org2 = factories.Organization()

        org_list = helpers.call_action("organization_list")

        assert sorted(org_list) == sorted([g["name"] for g in [org1, org2]])

    def test_organization_list_in_presence_of_groups(self):
        """
        Getting the organization_list only returns organization group
        types.
        """
        org1 = factories.Organization()
        org2 = factories.Organization()
        factories.Group()
        factories.Group()

        org_list = helpers.call_action("organization_list")

        assert sorted(org_list) == sorted([g["name"] for g in [org1, org2]])

    def test_organization_list_in_presence_of_custom_group_types(self):
        """
        Getting the organization_list only returns organization group
        types.
        """
        org1 = factories.Organization()
        org2 = factories.Organization()
        factories.Group(type="custom")
        factories.Group(type="custom")

        org_list = helpers.call_action("organization_list")

        assert sorted(org_list) == sorted([g["name"] for g in [org1, org2]])

    def test_organization_list_return_custom_organization_type(self):
        """
        Getting the org_list with a type defined should only return
        orgs of that type.
        """
        factories.Organization()
        org2 = factories.Organization(type="custom_org")
        factories.Group(type="custom")
        factories.Group(type="custom")

        org_list = helpers.call_action("organization_list", type="custom_org")

        assert sorted(org_list) == sorted([g["name"] for g in [org2]]), "{}".format(
            org_list
        )

    def _create_bulk_orgs(self, name, count):
        from ckan import model

        orgs = [
            model.Group(
                name="{}_{}".format(name, i),
                is_organization=True,
                type="organization",
            )
            for i in range(count)
        ]

        model.Session.add_all(orgs)
        model.repo.commit_and_remove()

    def test_limit_default(self):
        self._create_bulk_orgs("org_default", 1010)
        results = helpers.call_action("organization_list")
        assert len(results) == 1000  # i.e. default value

    @pytest.mark.ckan_config("ckan.group_and_organization_list_max", 5)
    def test_limit_configured(self):
        self._create_bulk_orgs("org_default", 7)
        results = helpers.call_action("organization_list")
        assert len(results) == 5  # i.e. configured limit

    @pytest.mark.ckan_config("ckan.group_and_organization_list_max", 5)
    def test_limit_with_custom_max_limit(self):
        self._create_bulk_orgs("org_default", 5)
        results = helpers.call_action("organization_list", limit=2)
        assert len(results) == 2

    def test_all_fields_limit_default(self):
        self._create_bulk_orgs("org_all_fields_default", 30)
        results = helpers.call_action("organization_list", all_fields=True)
        assert len(results) == 25  # i.e. default value

    @pytest.mark.ckan_config("ckan.group_and_organization_list_all_fields_max", 5)
    def test_all_fields_limit_with_custom_max_limit(self):
        self._create_bulk_orgs("org_all_fields_default", 5)
        results = helpers.call_action("organization_list", all_fields=True, limit=2)
        assert len(results) == 2

    @pytest.mark.ckan_config("ckan.group_and_organization_list_all_fields_max", 5)
    def test_all_fields_limit_configured(self):
        self._create_bulk_orgs("org_all_fields_default", 30)
        results = helpers.call_action("organization_list", all_fields=True)
        assert len(results) == 5  # i.e. configured limit


@pytest.mark.usefixtures("non_clean_db")
def test_organization_show():
    org = factories.Organization()

    org_dict = helpers.call_action(
        "organization_show", id=org["id"], include_datasets=True
    )

    org_dict.pop("packages", None)
    assert org_dict == org


@pytest.mark.usefixtures("non_clean_db")
def test_organization_show_error_not_found():

    with pytest.raises(logic.NotFound):
        helpers.call_action("organization_show", id="does_not_exist")


@pytest.mark.usefixtures("non_clean_db")
def test_organization_show_error_for_group():

    group = factories.Group()

    with pytest.raises(logic.NotFound):
        helpers.call_action("organization_show", id=group["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_organization_show_packages_returned():

    user_name = model.User.get_site_user().name

    org = factories.Organization()

    datasets = [
        {"name": factories.Dataset.stub().name, "owner_org": org["name"]},
        {"name": factories.Dataset.stub().name, "owner_org": org["name"]},
    ]

    for dataset in datasets:
        helpers.call_action("package_create", context={"user": user_name}, **dataset)

    org_dict = helpers.call_action(
        "organization_show", id=org["id"], include_datasets=True
    )

    assert len(org_dict["packages"]) == 2
    assert org_dict["package_count"] == 2


@pytest.mark.usefixtures("non_clean_db")
def test_organization_show_private_packages_not_returned():

    user_name = model.User.get_site_user().name

    org = factories.Organization()
    dataset1 = factories.Dataset.stub().name
    datasets = [
        {"name": dataset1, "owner_org": org["name"]},
        {
            "name": factories.Dataset.stub().name,
            "owner_org": org["name"],
            "private": True,
        },
    ]

    for dataset in datasets:
        helpers.call_action("package_create", context={"user": user_name}, **dataset)

    org_dict = helpers.call_action(
        "organization_show", id=org["id"], include_datasets=True
    )

    assert len(org_dict["packages"]) == 1
    assert org_dict["packages"][0]["name"] == dataset1
    assert org_dict["package_count"] == 1


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.search.rows_max", "2")
def test_package_limit_configured():
    org = factories.Organization()
    for _ in range(3):
        factories.Dataset(owner_org=org["id"])
    id = org["id"]

    results = helpers.call_action("organization_show", id=id, include_datasets=1)
    assert len(results["packages"]) == 2  # i.e. ckan.search.rows_max


@pytest.mark.usefixtures("clean_db")
class TestOrganizationListForUser(object):
    """Functional tests for the organization_list_for_user() action function."""

    def test_when_user_is_not_a_member_of_any_organizations(self):
        """
        When the user isn't a member of any organizations (in any capacity)
        organization_list_for_user() should return an empty list.
        """
        user = factories.User()
        context = {"user": user["name"]}

        # Create an organization so we can test that it does not get returned.
        factories.Organization()

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert organizations == []

    def test_when_user_is_an_admin_of_one_organization(self):
        """
        When the user is an admin of one organization
        organization_list_for_user() should return a list of just that one
        organization.
        """
        user = factories.User()
        context = {"user": user["name"]}
        organization = factories.Organization()

        # Create a second organization just so we can test that it does not get
        # returned.
        factories.Organization()

        helpers.call_action(
            "member_create",
            id=organization["id"],
            object=user["id"],
            object_type="user",
            capacity="admin",
        )

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert len(organizations) == 1
        assert organizations[0]["id"] == organization["id"]

    def test_when_user_is_an_admin_of_three_organizations(self):
        """
        When the user is an admin of three organizations
        organization_list_for_user() should return a list of all three
        organizations.
        """
        user = factories.User()
        context = {"user": user["name"]}
        organization_1 = factories.Organization()
        organization_2 = factories.Organization()
        organization_3 = factories.Organization()

        # Create a second organization just so we can test that it does not get
        # returned.
        factories.Organization()

        # Make the user an admin of all three organizations:
        for organization in (organization_1, organization_2, organization_3):
            helpers.call_action(
                "member_create",
                id=organization["id"],
                object=user["id"],
                object_type="user",
                capacity="admin",
            )

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert len(organizations) == 3
        ids = [organization["id"] for organization in organizations]
        for organization in (organization_1, organization_2, organization_3):
            assert organization["id"] in ids

    def test_when_permissions_extend_to_sub_organizations(self):
        """

        When the user is an admin of one organization
        organization_list_for_user() should return a list of just that one
        organization.

        """
        user = factories.User()
        context = {"user": user["name"]}
        user["capacity"] = "admin"
        top_organization = factories.Organization(users=[user])
        middle_organization = factories.Organization(users=[user])
        bottom_organization = factories.Organization()

        # Create another organization just so we can test that it does not get
        # returned.
        factories.Organization()

        helpers.call_action(
            "member_create",
            id=bottom_organization["id"],
            object=middle_organization["id"],
            object_type="group",
            capacity="parent",
        )
        helpers.call_action(
            "member_create",
            id=middle_organization["id"],
            object=top_organization["id"],
            object_type="group",
            capacity="parent",
        )

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert len(organizations) == 3
        org_ids = set(org["id"] for org in organizations)
        assert bottom_organization["id"] in org_ids

    def test_does_return_members(self):
        """
        By default organization_list_for_user() should return organizations
        that the user is just a member (not an admin) of.
        """
        user = factories.User()
        context = {"user": user["name"]}
        organization = factories.Organization()

        helpers.call_action(
            "member_create",
            id=organization["id"],
            object=user["id"],
            object_type="user",
            capacity="member",
        )

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert [org["id"] for org in organizations] == [organization["id"]]

    def test_does_return_editors(self):
        """
        By default organization_list_for_user() should return organizations
        that the user is just an editor (not an admin) of.
        """
        user = factories.User()
        context = {"user": user["name"]}
        organization = factories.Organization()

        helpers.call_action(
            "member_create",
            id=organization["id"],
            object=user["id"],
            object_type="user",
            capacity="editor",
        )

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert [org["id"] for org in organizations] == [organization["id"]]

    def test_editor_permission(self):
        """
        organization_list_for_user() should return organizations that the user
        is an editor of if passed a permission that belongs to the editor role.
        """
        user = factories.User()
        context = {"user": user["name"]}
        organization = factories.Organization()

        helpers.call_action(
            "member_create",
            id=organization["id"],
            object=user["id"],
            object_type="user",
            capacity="editor",
        )

        organizations = helpers.call_action(
            "organization_list_for_user",
            permission="create_dataset",
            context=context,
        )

        assert [org["id"] for org in organizations] == [organization["id"]]

    def test_member_permission(self):
        """
        organization_list_for_user() should return organizations that the user
        is a member of if passed a permission that belongs to the member role.
        """
        user = factories.User()
        context = {"user": user["name"]}
        organization = factories.Organization()

        helpers.call_action(
            "member_create",
            id=organization["id"],
            object=user["id"],
            object_type="user",
            capacity="member",
        )

        organizations = helpers.call_action(
            "organization_list_for_user", permission="read", context=context
        )

        assert [org["id"] for org in organizations] == [organization["id"]]

    def test_invalid_permission(self):
        """
        organization_list_for_user() should return an empty list if passed a
        non-existent or invalid permission.

        Note that we test this with a user who is an editor of one organization.
        If the user was an admin of the organization then it would return that
        organization - admins have all permissions, including permissions that
        don't exist.
        """
        user = factories.User()
        context = {"user": user["name"]}
        organization = factories.Organization()
        factories.Organization()
        helpers.call_action(
            "member_create",
            id=organization["id"],
            object=user["id"],
            object_type="user",
            capacity="editor",
        )

        for permission in ("", " ", "foo", 27.3, 5, True, False, None):
            organizations = helpers.call_action(
                "organization_list_for_user",
                permission=permission,
                context=context,
            )

        assert organizations == []

    def test_that_it_does_not_return_groups(self):
        """
        organization_list_for_user() should not return groups that the user is
        a member, editor or admin of.
        """
        user = factories.User()
        context = {"user": user["name"]}
        group_1 = factories.Group()
        group_2 = factories.Group()
        group_3 = factories.Group()
        helpers.call_action(
            "member_create",
            id=group_1["id"],
            object=user["id"],
            object_type="user",
            capacity="member",
        )
        helpers.call_action(
            "member_create",
            id=group_2["id"],
            object=user["id"],
            object_type="user",
            capacity="editor",
        )
        helpers.call_action(
            "member_create",
            id=group_3["id"],
            object=user["id"],
            object_type="user",
            capacity="admin",
        )

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert organizations == []

    def test_that_it_does_not_return_previous_memberships(self):
        """
        organization_list_for_user() should return organizations that the user
        was previously an admin of.
        """
        user = factories.User()
        context = {"user": user["name"]}
        organization = factories.Organization()

        # Make the user an admin of the organization.
        helpers.call_action(
            "member_create",
            id=organization["id"],
            object=user["id"],
            object_type="user",
            capacity="admin",
        )

        # Remove the user from the organization.
        helpers.call_action(
            "member_delete",
            id=organization["id"],
            object=user["id"],
            object_type="user",
        )

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert organizations == []

    def test_when_user_is_sysadmin(self):
        """
        When the user is a sysadmin organization_list_for_user() should just
        return all organizations, even if the user is not a member of them.
        """
        user = factories.Sysadmin()
        context = {"user": user["name"]}
        organization = factories.Organization()

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert [org["id"] for org in organizations] == [organization["id"]]

    def test_that_it_does_not_return_deleted_organizations(self):
        """
        organization_list_for_user() should not return deleted organizations
        that the user was an admin of.
        """
        user = factories.User()
        context = {"user": user["name"]}
        organization = factories.Organization()

        # Make the user an admin of the organization.
        helpers.call_action(
            "member_create",
            id=organization["id"],
            object=user["id"],
            object_type="user",
            capacity="admin",
        )

        # Delete the organization.
        helpers.call_action(
            "organization_delete", id=organization["id"], context=context
        )

        organizations = helpers.call_action(
            "organization_list_for_user", context=context
        )

        assert organizations == []

    def test_with_no_authorized_user(self):
        """
        organization_list_for_user() should return an empty list if there's no
        authorized user. Users who aren't logged-in don't have any permissions.
        """
        # Create an organization so we can test that it doesn't get returned.
        factories.Organization()

        organizations = helpers.call_action("organization_list_for_user")

        assert organizations == []

    def test_organization_list_for_user_returns_all_roles(self):

        user1 = factories.User()
        user2 = factories.User()
        user3 = factories.User()

        org1 = factories.Organization(
            users=[
                {"name": user1["name"], "capacity": "admin"},
                {"name": user2["name"], "capacity": "editor"},
            ]
        )
        org2 = factories.Organization(
            users=[
                {"name": user1["name"], "capacity": "member"},
                {"name": user2["name"], "capacity": "member"},
            ]
        )
        org3 = factories.Organization(
            users=[{"name": user1["name"], "capacity": "editor"}]
        )

        org_list_for_user1 = helpers.call_action(
            "organization_list_for_user", id=user1["id"]
        )

        assert sorted([org["id"] for org in org_list_for_user1]) == sorted(
            [org1["id"], org2["id"], org3["id"]]
        )

        org_list_for_user2 = helpers.call_action(
            "organization_list_for_user", id=user2["id"]
        )

        assert sorted([org["id"] for org in org_list_for_user2]) == sorted(
            [org1["id"], org2["id"]]
        )

        org_list_for_user3 = helpers.call_action(
            "organization_list_for_user", id=user3["id"]
        )

        assert org_list_for_user3 == []


@pytest.mark.usefixtures("non_clean_db")
def test_organization_patch_updating_single_field():
    user = factories.User()
    organization = factories.Organization(description="some test now", user=user)
    name = organization["name"]

    organization = helpers.call_action(
        "organization_patch",
        id=organization["id"],
        description="somethingnew",
        context={"user": user["name"]},
    )

    assert organization["name"] == name
    assert organization["description"] == "somethingnew"

    organization2 = helpers.call_action("organization_show", id=organization["id"])

    assert organization2["name"] == name
    assert organization2["description"] == "somethingnew"


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.public_user_details", "false")
def test_organization_patch_updating_single_field_when_public_user_details_is_false():
    user = factories.User()
    organization = factories.Organization(description="some test now", user=user)
    name = organization["name"]
    organization = helpers.call_action(
        "organization_patch",
        id=organization["id"],
        description="somethingnew",
        context={"user": user["name"]},
    )

    assert organization["name"] == name
    assert organization["description"] == "somethingnew"

    organization2 = helpers.call_action(
        "organization_show", id=organization["id"], include_users=True
    )

    assert organization2["name"] == name
    assert organization2["description"] == "somethingnew"
    assert len(organization2["users"]) == 1
    assert organization2["users"][0]["name"] == user["name"]


@pytest.mark.usefixtures("non_clean_db")
def test_update_organization_cant_change_type():
    user = factories.User()
    context = {"user": user["name"]}
    org = factories.Organization(type="organization", user=user)

    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "organization_update",
            context=context,
            id=org["id"],
            name=org["name"],
            type="ragtagband",
        )


@pytest.mark.usefixtures("non_clean_db")
def test_extras_removed_if_missing():
    org = factories.Organization(extras=[{"key": "e", "value": "v"}])
    assert org["extras"] == [{"key": "e", "value": "v"}]
    updated_org = helpers.call_action(
        "organization_update",
        id=org["name"],
    )

    assert updated_org["extras"] == []


@pytest.mark.usefixtures("non_clean_db")
def test_groups_unchanged_if_missing():
    group = factories.Group()
    org = factories.Organization(groups=[{"name": group["name"]}])
    assert org["groups"][0]["name"] == group["name"]
    updated_org = helpers.call_action(
        "organization_update",
        id=org["name"],
    )

    assert updated_org["groups"][0]["name"] == group["name"]


@pytest.mark.usefixtures("non_clean_db")
def test_groups_removed_if_empty_list():
    group = factories.Group()
    org = factories.Organization(groups=[{"name": group["name"]}])
    assert org["groups"][0]["name"] == group["name"]
    updated_org = helpers.call_action(
        "organization_update",
        id=org["name"],
        groups=[],
    )

    assert updated_org["groups"] == []


@pytest.mark.usefixtures("non_clean_db")
def test_users_unchanged_if_missing():
    user = factories.User()
    org = factories.Organization(users=[user])
    assert user["name"] in (g["name"] for g in org["users"])
    updated_org = helpers.call_action(
        "organization_update",
        id=org["name"],
    )

    assert user["name"] in (g["name"] for g in updated_org["users"])


@pytest.mark.usefixtures("non_clean_db")
def test_users_removed_if_empty_list():
    user = factories.User()
    org = factories.Organization(users=[user])
    assert user["name"] in (g["name"] for g in org["users"])
    updated_org = helpers.call_action("organization_update", id=org["name"], users=[])

    assert updated_org["users"] == []

def test_package_members_hide_private_datasets_from_unauthorized_users():
    org = factories.Organization()
    public_dataset = factories.Dataset(owner_org=org["id"], private=False)
    private_dataset = factories.Dataset(owner_org=org["id"], private=True)

    # Anonymous callers must only see the public dataset, not the private one
    org_members = helpers.call_action(
        "member_list", {"user": None}, id=org["id"], object_type="package"
    )

    member_ids = [m[0] for m in org_members]
    assert public_dataset["id"] in member_ids
    assert private_dataset["id"] not in member_ids

    # Organization members can see the private dataset, so they get both.
    member_user = factories.User()
    helpers.call_action(
        "organization_member_create",
        {"user": None, "ignore_auth": True},
        username=member_user["id"],
        id=org["id"],
        role="editor",
    )

    org_members = helpers.call_action(
        "member_list",
        {"user": member_user["name"]},
        id=org["id"],
        object_type="package",
    )

    member_ids = [m[0] for m in org_members]
    assert public_dataset["id"] in member_ids
    assert private_dataset["id"] in member_ids
