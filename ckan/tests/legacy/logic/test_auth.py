# encoding: utf-8

import json
import pytest

import ckan.authz as authz
import ckan.logic as logic
import ckan.model as model
import ckan.tests.factories as factories
from ckan.lib.create_test_data import CreateTestData
from ckan.logic import get_action
from ckan.tests.helpers import call_auth


@pytest.fixture
def auth_config(ckan_config, monkeypatch):
    options = (
        ("ckan.auth.anon_create_dataset", False),
        ("ckan.auth.create_dataset_if_not_in_organization", False),
        ("ckan.auth.user_create_groups", False),
        ("ckan.auth.user_create_organizations", False),
        ("ckan.auth.user_delete_groups", False),
        ("ckan.auth.user_delete_organizations", False),
        ("ckan.auth.create_unowned_dataset", False),
        ("ckan.auth.create_user_via_api", False),
        ("ckan.auth.create_user_via_web", True),
        ("ckan.auth.roles_that_cascade_to_sub_groups", "admin"),
    )
    for key, value in options:
        monkeypatch.setitem(ckan_config, key, value)


@pytest.fixture
def apikeys(clean_db):
    admin_api = get_action("get_site_user")(
        {"model": model, "ignore_auth": True}, {}
    )["apikey"]
    return {"sysadmin": str(admin_api), "random_key": "moo"}


@pytest.fixture
def call_api(app, apikeys):
    def call(action, data, user, status=None):

        res = app.post(
            "/api/action/%s" % action,
            json=data,
            extra_environ={"Authorization": apikeys[user]},
        )
        if res.status_code != (status or 200):
            error = res.json["error"]
            raise AssertionError(
                "Status was %s but should be %s. Error: %s"
                % (res.status_code, status, error)
            )
        return res

    return call


@pytest.fixture
def create_user(apikeys, call_api):
    def create(name):
        user = {
            "name": name,
            "password": "TestPassword1",
            "email": "{}@moo.com".format(name),
        }
        res = call_api("user_create", user, "sysadmin", 200)
        apikeys[name] = str(json.loads(res.body)["result"]["apikey"])

    return create


@pytest.mark.usefixtures("clean_db", "auth_config", "with_request_context")
def test_only_sysadmins_can_delete_users():
    user = factories.User()
    sysadmin = factories.Sysadmin()

    context = {"model": model, "user": user["name"]}
    with pytest.raises(logic.NotAuthorized):
        assert not call_auth("user_delete", context=context, id=user["id"])

    context = {"model": model, "user": sysadmin["name"]}
    assert call_auth("user_delete", context=context, id=user["id"])


@pytest.mark.usefixtures("clean_db", "auth_config", "with_request_context")
def test_auth_deleted_users_are_always_unauthorized():
    always_success = lambda x, y: {"success": True}
    authz._AuthFunctions._build()
    authz._AuthFunctions._functions["always_success"] = always_success
    username = "deleted_user"
    user_obj = factories.User()
    username = user_obj["name"]
    user = model.User.get(username)
    user.delete()
    assert not authz.is_authorized_boolean(
        "always_success", {"user": username}
    )
    del authz._AuthFunctions._functions["always_success"]


class TestAuthOrgs(object):
    @pytest.fixture(autouse=True)
    def initial_data(self, create_user):
        # actual roles assigned later
        create_user("org_admin")
        create_user("no_org")
        create_user("org_editor")
        create_user("editor_wannabe")

    def _add_datasets(self, user, call_api):
        # org admin/editor should be able to add dataset to org.
        dataset = {"name": user + "_dataset", "owner_org": "org_with_user"}
        call_api("package_create", dataset, user, 200)

        # not able to add dataset to org admin does not belong to.
        dataset = {"name": user + "_dataset_bad", "owner_org": "org_no_user"}
        call_api("package_create", dataset, user, 403)

        # admin not able to make dataset not owned by a org
        dataset = {"name": user + "_dataset_bad"}
        call_api("package_create", dataset, user, 409)

        # not able to add org to not existant org
        dataset = {"name": user + "_dataset_bad", "owner_org": "org_not_exist"}
        call_api("package_create", dataset, user, 403)

    def _update_datasets(self, user, call_api):
        ##editor/admin should be able to update dataset
        dataset = {"id": "org_editor_dataset", "title": "test"}
        call_api("package_update", dataset, user, 200)
        # editor/admin tries to change owner org
        dataset = {"id": "org_editor_dataset", "owner_org": "org_no_user"}
        call_api("package_update", dataset, user, 409)
        # editor/admin tries to update dataset in different org
        dataset = {"id": "sysadmin_create_no_user", "title": "test"}
        call_api("package_update", dataset, user, 403)
        # non existant owner org
        dataset = {"id": "org_editor_dataset", "owner_org": "org_not_exist"}
        call_api("package_update", dataset, user, 409)

    def _delete_datasets(self, user, call_api):
        # editor/admin should be able to update dataset
        dataset = {"id": "org_editor_dataset"}
        call_api("package_delete", dataset, user, 200)
        # not able to delete dataset in org user does not belong to
        dataset = {"id": "sysadmin_create_no_user"}
        call_api("package_delete", dataset, user, 403)

    def test_create_users(self, call_api):
        user = {
            "name": "user_no_auth",
            "password": "TestPassword1",
            "email": "moo@moo.com",
        }

        call_api("user_create", user, "random_key", 403)
        call_api("user_create", user, "no_org", 403)

    @pytest.mark.usefixtures("auth_config")
    def test_create_dataset_no_org(self, call_api):

        # no owner_org supplied
        dataset = {"name": "admin_create_no_org"}
        call_api("package_create", dataset, "sysadmin", 409)

        dataset = {"name": "should_not_be_created"}
        call_api("package_create", dataset, "no_org", 403)

    @pytest.mark.usefixtures("auth_config")
    def test_02_create_orgs(self, call_api):
        org = {"name": "org_no_user"}
        call_api("organization_create", org, "random_key", 403)
        call_api("organization_create", org, "sysadmin")

        org = {"name": "org_with_user"}
        call_api("organization_create", org, "random_key", 403)
        call_api("organization_create", org, "sysadmin")

        # no user should be able to create org
        org = {"name": "org_should_not_be_created"}
        call_api("organization_create", org, "org_admin", 403)

        # def test_04_create_dataset_with_org(self):
        org_with_user = call_api(
            "organization_show", {"id": "org_with_user"}, "sysadmin"
        )
        dataset = {
            "name": "admin_create_with_user",
            "owner_org": org_with_user.json["result"]["id"],
        }
        call_api("package_create", dataset, "sysadmin", 200)

        org_no_user = call_api(
            "organization_show", {"id": "org_no_user"}, "sysadmin"
        )
        dataset = {
            "name": "sysadmin_create_no_user",
            "owner_org": org_no_user.json["result"]["id"],
        }
        call_api("package_create", dataset, "sysadmin", 200)
        dataset = {
            "name": "user_create_with_org",
            "owner_org": org_with_user.json["result"]["id"],
        }

        # def test_05_add_users_to_org(self):

        member = {
            "username": "org_admin",
            "role": "admin",
            "id": "org_with_user",
        }
        call_api("organization_member_create", member, "sysadmin")

        ## admin user should be able to add users now
        member = {
            "username": "org_editor",
            "role": "editor",
            "id": "org_with_user",
        }
        call_api("organization_member_create", member, "org_admin")

        ## editor should not be able to approve others as editors
        member = {
            "username": "editor_wannabe",
            "role": "editor",
            "id": "org_with_user",
        }
        call_api("organization_member_create", member, "org_editor", 403)

        # def test_07_add_datasets(self):
        self._add_datasets("org_admin", call_api)
        self._add_datasets("org_editor", call_api)

        # def test_08_update_datasets(self):
        self._update_datasets("org_admin", call_api)
        self._update_datasets("org_editor", call_api)

        # def test_09_delete_datasets(self):
        self._delete_datasets("org_admin", call_api)
        self._delete_datasets("org_editor", call_api)

        # def test_10_edit_org(self):
        org = {"id": "org_no_user", "title": "test"}
        # change an org user does not belong to
        call_api("organization_update", org, "org_editor", 403)
        call_api("organization_update", org, "org_admin", 403)

        # change an org a user belongs to
        org = {"id": "org_with_user", "title": "test"}
        call_api("organization_update", org, "org_editor", 403)
        call_api("organization_update", org, "org_admin", 200)

        # def test_11_delete_org(self):
        org = {"id": "org_no_user", "title": "test"}
        call_api("organization_delete", org, "org_editor", 403)
        call_api("organization_delete", org, "org_admin", 403)
        org = {"id": "org_with_user"}
        call_api("organization_delete", org, "org_editor", 403)
        call_api("organization_delete", org, "org_admin", 403)


class TestAuthOrgHierarchy(object):
    # Tests are in the same vein as TestAuthOrgs, testing the cases where the
    # group hierarchy provides extra permissions through cascading

    @pytest.fixture(autouse=True)
    def initial_data(self, apikeys, monkeypatch, ckan_config):
        monkeypatch.setitem(
            ckan_config, "ckan.auth.roles_that_cascade_to_sub_groups", "admin"
        )
        CreateTestData.create_group_hierarchy_test_data()
        for user in model.Session.query(model.User):
            apikeys[user.name] = str(user.apikey)

        self.sysadmin = get_action("get_site_user")(
            {"model": model, "ignore_auth": True}, {}
        )

        CreateTestData.create_arbitrary(
            package_dicts=[
                {"name": "adataset", "groups": ["national-health-service"]}
            ],
            extra_user_names=["john"],
        )

    def _reset_a_datasets_owner_org(self):
        get_action("package_owner_org_update")(
            {
                "model": model,
                "user": self.sysadmin["name"],
                "ignore_auth": True,
            },
            {"id": "adataset", "organization_id": "national-health-service"},
        )

    def _undelete_package_if_needed(self, package_name):
        pkg = model.Package.by_name(package_name)
        if pkg and pkg.state == "deleted":
            pkg.state = "active"
            model.repo.commit_and_remove()

    def test_05_add_users_to_org_1(self, call_api):
        member = {
            "username": "john",
            "role": "admin",
            "id": "department-of-health",
        }
        call_api("organization_member_create", member, "nhsadmin", 403)
        # def test_05_add_users_to_org_2(self):
        member = {
            "username": "john",
            "role": "editor",
            "id": "department-of-health",
        }
        call_api("organization_member_create", member, "nhsadmin", 403)
        # def test_05_add_users_to_org_3(self):
        member = {
            "username": "john",
            "role": "admin",
            "id": "national-health-service",
        }
        call_api("organization_member_create", member, "nhsadmin", 200)
        # def test_05_add_users_to_org_4(self):
        member = {
            "username": "john",
            "role": "editor",
            "id": "national-health-service",
        }
        call_api("organization_member_create", member, "nhsadmin", 200)
        # def test_05_add_users_to_org_5(self):
        member = {"username": "john", "role": "admin", "id": "nhs-wirral-ccg"}
        call_api("organization_member_create", member, "nhsadmin", 200)
        # def test_05_add_users_to_org_6(self):
        member = {"username": "john", "role": "editor", "id": "nhs-wirral-ccg"}
        call_api("organization_member_create", member, "nhsadmin", 200)
        # def test_05_add_users_to_org_7(self):
        member = {
            "username": "john",
            "role": "editor",
            "id": "national-health-service",
        }
        call_api("organization_member_create", member, "nhseditor", 403)

        # def test_07_add_datasets_1(self, call_api):
        dataset = {"name": "t1", "owner_org": "department-of-health"}
        call_api("package_create", dataset, "nhsadmin", 403)

        # def test_07_add_datasets_2(self):
        dataset = {"name": "t2", "owner_org": "national-health-service"}
        call_api("package_create", dataset, "nhsadmin", 200)

        # def test_07_add_datasets_3(self):
        dataset = {"name": "t3", "owner_org": "nhs-wirral-ccg"}
        call_api("package_create", dataset, "nhsadmin", 200)

        # def test_07_add_datasets_4(self):
        dataset = {"name": "t4", "owner_org": "department-of-health"}
        call_api("package_create", dataset, "nhseditor", 403)

        # def test_07_add_datasets_5(self):
        dataset = {"name": "t5", "owner_org": "national-health-service"}
        call_api("package_create", dataset, "nhseditor", 200)

        # def test_07_add_datasets_6(self):
        dataset = {"name": "t6", "owner_org": "nhs-wirral-ccg"}
        call_api("package_create", dataset, "nhseditor", 403)

        # def test_08_update_datasets_1(self, call_api):
        dataset = {"name": "adataset", "owner_org": "department-of-health"}
        call_api("package_update", dataset, "nhsadmin", 409)

        # def test_08_update_datasets_2(self):
        dataset = {"name": "adataset", "owner_org": "national-health-service"}
        call_api("package_update", dataset, "nhsadmin", 200)

        # def test_08_update_datasets_3(self):
        dataset = {"name": "adataset", "owner_org": "nhs-wirral-ccg"}
        try:
            call_api("package_update", dataset, "nhsadmin", 200)
        finally:
            self._reset_a_datasets_owner_org()

        # def test_08_update_datasets_4(self):
        dataset = {"name": "adataset", "owner_org": "department-of-health"}
        call_api("package_update", dataset, "nhseditor", 409)

        # def test_08_update_datasets_5(self):
        dataset = {"name": "adataset", "owner_org": "national-health-service"}
        try:
            call_api("package_update", dataset, "nhseditor", 200)
        finally:
            self._reset_a_datasets_owner_org()

        # def test_08_update_datasets_6(self):
        dataset = {"name": "adataset", "owner_org": "nhs-wirral-ccg"}
        call_api("package_update", dataset, "nhseditor", 409)

        # def test_09_delete_datasets_1(self, call_api):
        dataset = {"id": "doh-spend"}
        try:
            call_api("package_delete", dataset, "nhsadmin", 403)
        finally:
            self._undelete_package_if_needed(dataset["id"])

        # def test_09_delete_datasets_2(self):
        dataset = {"id": "nhs-spend"}
        try:
            call_api("package_delete", dataset, "nhsadmin", 200)
        finally:
            self._undelete_package_if_needed(dataset["id"])

        # def test_09_delete_datasets_3(self):
        dataset = {"id": "wirral-spend"}
        try:
            call_api("package_delete", dataset, "nhsadmin", 200)
        finally:
            self._undelete_package_if_needed(dataset["id"])

        # def test_09_delete_datasets_4(self):
        dataset = {"id": "nhs-spend"}
        try:
            call_api("package_delete", dataset, "nhseditor", 200)
        finally:
            self._undelete_package_if_needed(dataset["id"])

        # def test_09_delete_datasets_5(self):
        dataset = {"id": "wirral-spend"}
        try:
            call_api("package_delete", dataset, "nhseditor", 403)
        finally:
            self._undelete_package_if_needed(dataset["id"])

        # def test_10_edit_org_1(self, call_api):
        org = {"id": "department-of-health", "title": "test"}
        self._flesh_out_organization(org)
        call_api("organization_update", org, "nhsadmin", 403)

        # def test_10_edit_org_2(self):
        org = {"id": "national-health-service", "title": "test"}
        self._flesh_out_organization(org)
        call_api("organization_update", org, "nhsadmin", 200)

        # def test_10_edit_org_3(self):
        org = {"id": "nhs-wirral-ccg", "title": "test"}
        self._flesh_out_organization(org)
        call_api("organization_update", org, "nhsadmin", 200)

        # def test_10_edit_org_4(self):
        org = {"id": "department-of-health", "title": "test"}
        self._flesh_out_organization(org)
        call_api("organization_update", org, "nhseditor", 403)

        # def test_10_edit_org_5(self):
        org = {"id": "national-health-service", "title": "test"}
        self._flesh_out_organization(org)
        call_api("organization_update", org, "nhseditor", 403)

        # def test_10_edit_org_6(self):
        org = {"id": "nhs-wirral-ccg", "title": "test"}
        self._flesh_out_organization(org)
        call_api("organization_update", org, "nhseditor", 403)

        # def test_11_delete_org_1(self, call_api):
        org = {"id": "department-of-health"}
        call_api("organization_delete", org, "nhsadmin", 403)
        call_api("organization_delete", org, "nhseditor", 403)

        # def test_11_delete_org_2(self):
        org = {"id": "national-health-service"}
        call_api("organization_delete", org, "nhsadmin", 200)
        call_api("organization_delete", org, "nhseditor", 403)

        # def test_11_delete_org_3(self):
        org = {"id": "nhs-wirral-ccg"}
        call_api("organization_delete", org, "nhsadmin", 403)
        call_api("organization_delete", org, "nhseditor", 403)

    def _flesh_out_organization(self, org):
        # When calling organization_update, unless you include the list of
        # editor and admin users and parent groups, it will remove them. So
        # get the current list
        existing_org = get_action("organization_show")(
            {"model": model, "ignore_auth": True}, {"id": org["id"]}
        )
        org.update(existing_org)


class TestAuthGroups(object):
    @pytest.mark.usefixtures("auth_config")
    def test_auth_groups(self, call_api, create_user):
        group = {"name": "group_no_user"}
        call_api("group_create", group, "random_key", 403)
        call_api("group_create", group, "sysadmin")

        group = {"name": "group_with_user"}
        call_api("group_create", group, "random_key", 403)
        call_api("group_create", group, "sysadmin")

        # def test_02_add_users_to_group(self):
        create_user("org_admin")
        create_user("org_editor")
        create_user("org_editor_wannabe")
        create_user("no_group")

        member = {
            "username": "org_admin",
            "role": "admin",
            "id": "group_with_user",
        }
        call_api("group_member_create", member, "sysadmin")

        ## admin user should be able to add users now
        member = {
            "username": "org_editor",
            "role": "editor",
            "id": "group_with_user",
        }
        call_api("group_member_create", member, "org_admin")

        ## editor should not be able to approve others as editors
        member = {
            "username": "org_editor_wannabe",
            "role": "editor",
            "id": "group_with_user",
        }
        call_api("group_member_create", member, "org_editor", 403)

        # def test_03_add_dataset_to_group(self):
        org = {"name": "org"}
        call_api("organization_create", org, "sysadmin")
        package = {"name": "package_added_by_admin", "owner_org": "org"}
        call_api("package_create", package, "sysadmin")
        package = {"name": "package_added_by_editor", "owner_org": "org"}
        call_api("package_create", package, "sysadmin")

        res = call_api("group_show", {"id": "group_with_user"}, "org_admin")
        group = json.loads(res.body)["result"]
        call_api("group_update", group, "no_group", 403)
        call_api("group_update", group, "org_admin")

        group = {
            "id": "group_with_user",
            "packages": [
                {"id": "package_added_by_admin"},
                {"id": "package_added_by_editor"},
            ],
        }
        # org editor doesn't have edit rights
        call_api("group_update", group, "org_editor", 403)

        # def test_04_modify_group(self):
        res = call_api("group_show", {"id": "group_with_user"}, "org_admin")
        group = json.loads(res.body)["result"]
        group.update(
            {"title": "moo", "packages": [{"id": "package_added_by_admin"}]}
        )
        call_api("group_update", group, "org_admin")

        # need to think about this as is horrible may just let editor edit
        # group for this case even though spec says otherwise
        call_api("group_update", group, "org_editor", 403)

        # def test_05_delete_group(self):
        org = {"id": "group_with_user"}
        call_api("group_delete", org, "org_editor", 403)
        call_api("group_delete", org, "org_admin", 403)
        org = {"id": "group_with_user"}
        call_api("group_delete", org, "org_editor", 403)
        call_api("group_delete", org, "org_admin", 403)
