# encoding: utf-8

import pytest
from bs4 import BeautifulSoup
from mock import patch

from ckan import model
from ckan.lib.helpers import url_for
from ckan.tests import factories, helpers
from ckan.tests.helpers import webtest_submit, submit_and_follow


@pytest.mark.usefixtures("clean_db")
class TestOrganizationNew(object):
    @pytest.fixture
    def user_env(self):
        user = factories.User()
        return {"REMOTE_USER": user["name"].encode("ascii")}

    def test_not_logged_in(self, app):
        app.get(url=url_for("group.new"), status=403)

    def test_name_required(self, app, user_env):
        response = app.get(
            url=url_for("organization.new"), extra_environ=user_env
        )
        form = response.forms["organization-edit-form"]
        response = webtest_submit(form, name="save", extra_environ=user_env)

        assert "organization-edit-form" in response.forms
        assert "Name: Missing value" in response

    def test_saved(self, app, user_env):
        response = app.get(
            url=url_for("organization.new"), extra_environ=user_env
        )

        form = response.forms["organization-edit-form"]
        form["name"] = u"saved"

        response = submit_and_follow(
            app, form, name="save", extra_environ=user_env
        )
        group = helpers.call_action("organization_show", id="saved")
        assert group["title"] == u""
        assert group["type"] == "organization"
        assert group["state"] == "active"

    def test_all_fields_saved(self, app, user_env):
        response = app.get(
            url=url_for("organization.new"), extra_environ=user_env
        )

        form = response.forms["organization-edit-form"]
        form["name"] = u"all-fields-saved"
        form["title"] = "Science"
        form["description"] = "Sciencey datasets"
        form["image_url"] = "http://example.com/image.png"

        response = submit_and_follow(
            app, form, name="save", extra_environ=user_env
        )
        group = helpers.call_action("organization_show", id="all-fields-saved")
        assert group["title"] == u"Science"
        assert group["description"] == "Sciencey datasets"


class TestOrganizationList(object):
    @patch(
        "ckan.logic.auth.get.organization_list",
        return_value={"success": False},
    )
    @pytest.mark.usefixtures("clean_db")
    def test_error_message_shown_when_no_organization_list_permission(
        self, mock_check_access, app
    ):
        self.user = factories.User()
        self.user_env = {"REMOTE_USER": self.user["name"].encode("ascii")}
        self.organization_list_url = url_for("organization.index")

        response = app.get(
            url=self.organization_list_url,
            extra_environ=self.user_env,
            status=403,
        )


@pytest.mark.usefixtures("clean_db")
class TestOrganizationRead(object):
    def test_group_read(self, app):
        org = factories.Organization()
        response = app.get(url=url_for("organization.read", id=org["name"]))
        assert org["title"] in response
        assert org["description"] in response

    def test_read_redirect_when_given_id(self, app):
        org = factories.Organization()
        response = app.get(
            url_for("organization.read", id=org["id"]), status=302
        )
        # redirect replaces the ID with the name in the URL
        redirected_response = response.follow()
        expected_url = url_for("organization.read", id=org["name"])
        assert redirected_response.request.path == expected_url

    def test_no_redirect_loop_when_name_is_the_same_as_the_id(self, app):
        org = factories.Organization(id="abc", name="abc")
        app.get(
            url_for("organization.read", id=org["id"]), status=200
        )  # ie no redirect


@pytest.mark.usefixtures("clean_db")
class TestOrganizationEdit(object):
    @pytest.fixture
    def initial_data(self):
        user = factories.User()
        return {
            "user": user,
            "user_env": {"REMOTE_USER": user["name"].encode("ascii")},
            "organization": factories.Organization(user=user),
        }

    def test_group_doesnt_exist(self, app, initial_data):
        url = url_for("organization.edit", id="doesnt_exist")
        app.get(url=url, extra_environ=initial_data["user_env"], status=404)

    def test_saved(self, app, initial_data):
        response = app.get(
            url=url_for(
                "organization.edit", id=initial_data["organization"]["id"]
            ),
            extra_environ=initial_data["user_env"],
        )

        form = response.forms["organization-edit-form"]
        response = webtest_submit(
            form, name="save", extra_environ=initial_data["user_env"]
        )
        group = helpers.call_action(
            "organization_show", id=initial_data["organization"]["id"]
        )
        assert group["title"] == u"Test Organization"
        assert group["type"] == "organization"
        assert group["state"] == "active"

    def test_all_fields_saved(self, app, initial_data):
        response = app.get(
            url=url_for(
                "organization.edit", id=initial_data["organization"]["id"]
            ),
            extra_environ=initial_data["user_env"],
        )

        form = response.forms["organization-edit-form"]
        form["name"] = u"all-fields-edited"
        form["title"] = "Science"
        form["description"] = "Sciencey datasets"
        form["image_url"] = "http://example.com/image.png"
        response = webtest_submit(
            form, name="save", extra_environ=initial_data["user_env"]
        )

        group = helpers.call_action(
            "organization_show", id=initial_data["organization"]["id"]
        )
        assert group["title"] == u"Science"
        assert group["description"] == "Sciencey datasets"
        assert group["image_url"] == "http://example.com/image.png"


@pytest.mark.usefixtures("clean_db")
class TestOrganizationDelete(object):
    @pytest.fixture
    def initial_data(self):
        user = factories.User()
        return {
            "user": user,
            "user_env": {"REMOTE_USER": user["name"].encode("ascii")},
            "organization": factories.Organization(user=user),
        }

    def test_owner_delete(self, app, initial_data):
        response = app.get(
            url=url_for(
                "organization.delete", id=initial_data["organization"]["id"]
            ),
            status=200,
            extra_environ=initial_data["user_env"],
        )

        form = response.forms["organization-confirm-delete-form"]
        response = submit_and_follow(
            app, form, name="delete", extra_environ=initial_data["user_env"]
        )
        organization = helpers.call_action(
            "organization_show", id=initial_data["organization"]["id"]
        )
        assert organization["state"] == "deleted"

    def test_sysadmin_delete(self, app, initial_data):
        sysadmin = factories.Sysadmin()
        extra_environ = {"REMOTE_USER": sysadmin["name"].encode("ascii")}
        response = app.get(
            url=url_for(
                "organization.delete", id=initial_data["organization"]["id"]
            ),
            status=200,
            extra_environ=extra_environ,
        )

        form = response.forms["organization-confirm-delete-form"]
        response = submit_and_follow(
            app, form, name="delete", extra_environ=initial_data["user_env"]
        )
        organization = helpers.call_action(
            "organization_show", id=initial_data["organization"]["id"]
        )
        assert organization["state"] == "deleted"

    def test_non_authorized_user_trying_to_delete_fails(
        self, app, initial_data
    ):
        user = factories.User()
        extra_environ = {"REMOTE_USER": user["name"].encode("ascii")}
        app.get(
            url=url_for(
                "organization.delete", id=initial_data["organization"]["id"]
            ),
            status=403,
            extra_environ=extra_environ,
        )

        organization = helpers.call_action(
            "organization_show", id=initial_data["organization"]["id"]
        )
        assert organization["state"] == "active"

    def test_anon_user_trying_to_delete_fails(self, app, initial_data):
        app.get(
            url=url_for(
                "organization.delete", id=initial_data["organization"]["id"]
            ),
            status=403,
        )

        organization = helpers.call_action(
            "organization_show", id=initial_data["organization"]["id"]
        )
        assert organization["state"] == "active"

    @pytest.mark.ckan_config("ckan.auth.create_unowned_dataset", False)
    def test_delete_organization_with_datasets(self, app, initial_data):
        """ Test deletion of organization that has datasets"""
        text = "Organization cannot be deleted while it still has datasets"
        datasets = [
            factories.Dataset(owner_org=initial_data["organization"]["id"])
            for i in range(0, 5)
        ]
        response = app.get(
            url=url_for(
                "organization.delete", id=initial_data["organization"]["id"]
            ),
            status=200,
            extra_environ=initial_data["user_env"],
        )

        form = response.forms["organization-confirm-delete-form"]
        response = submit_and_follow(
            app, form, name="delete", extra_environ=initial_data["user_env"]
        )
        assert text in response.body

    def test_delete_organization_with_unknown_dataset_true(self, initial_data):
        """ Test deletion of organization that has datasets and unknown
            datasets are set to true"""
        dataset = factories.Dataset(
            owner_org=initial_data["organization"]["id"]
        )
        assert dataset["owner_org"] == initial_data["organization"]["id"]
        user = factories.User()
        helpers.call_action(
            "organization_delete",
            id=initial_data["organization"]["id"],
            context={"user": user["name"]},
        )

        dataset = helpers.call_action("package_show", id=dataset["id"])
        assert dataset["owner_org"] is None


@pytest.mark.usefixtures("clean_db")
class TestOrganizationBulkProcess(object):
    def test_make_private(self, app):
        self.user = factories.User()
        self.user_env = {"REMOTE_USER": self.user["name"].encode("ascii")}
        self.organization = factories.Organization(user=self.user)

        datasets = [
            factories.Dataset(owner_org=self.organization["id"], private=False)
            for i in range(0, 5)
        ]
        response = app.get(
            url=url_for(
                "organization.bulk_process", id=self.organization["id"]
            ),
            extra_environ=self.user_env,
        )
        form = response.forms[2]
        for v in form.fields.values():
            try:
                v[0].checked = True
            except AttributeError:
                pass
        response = webtest_submit(
            form,
            name="bulk_action.private",
            value="private",
            extra_environ=self.user_env,
        )

        for dataset in datasets:
            d = helpers.call_action("package_show", id=dataset["id"])
            assert d["private"]

    def test_make_public(self, app):
        self.user = factories.User()
        self.user_env = {"REMOTE_USER": self.user["name"].encode("ascii")}
        self.organization = factories.Organization(user=self.user)

        datasets = [
            factories.Dataset(owner_org=self.organization["id"], private=True)
            for i in range(0, 5)
        ]
        response = app.get(
            url=url_for(
                "organization.bulk_process", id=self.organization["id"]
            ),
            extra_environ=self.user_env,
        )
        form = response.forms[2]
        for v in form.fields.values():
            try:
                v[0].checked = True
            except AttributeError:
                pass
        response = webtest_submit(
            form,
            name="bulk_action.public",
            value="public",
            extra_environ=self.user_env,
        )

        for dataset in datasets:
            d = helpers.call_action("package_show", id=dataset["id"])
            assert not (d["private"])

    def test_delete(self, app):
        self.user = factories.User()
        self.user_env = {"REMOTE_USER": self.user["name"].encode("ascii")}
        self.organization = factories.Organization(user=self.user)
        datasets = [
            factories.Dataset(owner_org=self.organization["id"], private=True)
            for i in range(0, 5)
        ]
        response = app.get(
            url=url_for(
                "organization.bulk_process", id=self.organization["id"]
            ),
            extra_environ=self.user_env,
        )
        form = response.forms[2]
        for v in form.fields.values():
            try:
                v[0].checked = True
            except AttributeError:
                pass
        response = webtest_submit(
            form,
            name="bulk_action.delete",
            value="delete",
            extra_environ=self.user_env,
        )

        for dataset in datasets:
            d = helpers.call_action("package_show", id=dataset["id"])
            assert d["state"] == "deleted"


@pytest.mark.usefixtures("clean_db")
class TestOrganizationSearch(object):
    """Test searching for organizations."""

    def test_organization_search(self, app):
        """Requesting organization search (index) returns list of
        organizations and search form."""

        factories.Organization(name="org-one", title="AOrg One")
        factories.Organization(name="org-two", title="AOrg Two")
        factories.Organization(name="org-three", title="Org Three")

        index_response = app.get(url_for("organization.index"))
        index_response_html = BeautifulSoup(index_response.body)
        org_names = index_response_html.select(
            "ul.media-grid " "li.media-item " "h3.media-heading"
        )
        org_names = [n.string for n in org_names]

        assert len(org_names) == 3
        assert "AOrg One" in org_names
        assert "AOrg Two" in org_names
        assert "Org Three" in org_names

    def test_organization_search_results(self, app):
        """Searching via organization search form returns list of expected
        organizations."""
        factories.Organization(name="org-one", title="AOrg One")
        factories.Organization(name="org-two", title="AOrg Two")
        factories.Organization(name="org-three", title="Org Three")

        index_response = app.get(url_for("organization.index"))
        search_form = index_response.forms["organization-search-form"]
        search_form["q"] = "AOrg"
        search_response = webtest_submit(search_form)

        search_response_html = BeautifulSoup(search_response.body)
        org_names = search_response_html.select(
            "ul.media-grid " "li.media-item " "h3.media-heading"
        )
        org_names = [n.string for n in org_names]

        assert len(org_names) == 2
        assert "AOrg One" in org_names
        assert "AOrg Two" in org_names
        assert "Org Three" not in org_names

    def test_organization_search_no_results(self, app):
        """Searching with a term that doesn't apply returns no results."""
        factories.Organization(name="org-one", title="AOrg One")
        factories.Organization(name="org-two", title="AOrg Two")
        factories.Organization(name="org-three", title="Org Three")

        index_response = app.get(url_for("organization.index"))
        search_form = index_response.forms["organization-search-form"]
        search_form["q"] = "No Results Here"
        search_response = webtest_submit(search_form)

        search_response_html = BeautifulSoup(search_response.body)
        org_names = search_response_html.select(
            "ul.media-grid " "li.media-item " "h3.media-heading"
        )
        org_names = [n.string for n in org_names]

        assert len(org_names) == 0
        assert (
            'No organizations found for "No Results Here"'
            in search_response.body
        )


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestOrganizationInnerSearch(object):
    """Test searching within an organization."""

    def test_organization_search_within_org(self, app):
        """Organization read page request returns list of datasets owned by
        organization."""
        org = factories.Organization()
        factories.Dataset(
            name="ds-one", title="Dataset One", owner_org=org["id"]
        )
        factories.Dataset(
            name="ds-two", title="Dataset Two", owner_org=org["id"]
        )
        factories.Dataset(
            name="ds-three", title="Dataset Three", owner_org=org["id"]
        )

        org_url = url_for("organization.read", id=org["name"])
        org_response = app.get(org_url)
        org_response_html = BeautifulSoup(org_response.body)

        ds_titles = org_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        ds_titles = [t.string for t in ds_titles]

        assert "3 datasets found" in org_response
        assert len(ds_titles) == 3
        assert "Dataset One" in ds_titles
        assert "Dataset Two" in ds_titles
        assert "Dataset Three" in ds_titles

    def test_organization_search_within_org_results(self, app):
        """Searching within an organization returns expected dataset
        results."""
        org = factories.Organization()
        factories.Dataset(
            name="ds-one", title="Dataset One", owner_org=org["id"]
        )
        factories.Dataset(
            name="ds-two", title="Dataset Two", owner_org=org["id"]
        )
        factories.Dataset(
            name="ds-three", title="Dataset Three", owner_org=org["id"]
        )

        org_url = url_for("organization.read", id=org["name"])
        org_response = app.get(org_url)
        search_form = org_response.forms["organization-datasets-search-form"]
        search_form["q"] = "One"
        search_response = webtest_submit(search_form)
        assert "1 dataset found for &#34;One&#34;" in search_response

        search_response_html = BeautifulSoup(search_response.body)

        ds_titles = search_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        ds_titles = [t.string for t in ds_titles]

        assert len(ds_titles) == 1
        assert "Dataset One" in ds_titles
        assert "Dataset Two" not in ds_titles
        assert "Dataset Three" not in ds_titles

    def test_organization_search_within_org_no_results(self, app):
        """Searching for non-returning phrase within an organization returns
        no results."""

        org = factories.Organization()
        factories.Dataset(
            name="ds-one", title="Dataset One", owner_org=org["id"]
        )
        factories.Dataset(
            name="ds-two", title="Dataset Two", owner_org=org["id"]
        )
        factories.Dataset(
            name="ds-three", title="Dataset Three", owner_org=org["id"]
        )

        org_url = url_for("organization.read", id=org["name"])
        org_response = app.get(org_url)
        search_form = org_response.forms["organization-datasets-search-form"]
        search_form["q"] = "Nout"
        search_response = webtest_submit(search_form)

        assert 'No datasets found for "Nout"' in search_response.body

        search_response_html = BeautifulSoup(search_response.body)

        ds_titles = search_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        ds_titles = [t.string for t in ds_titles]

        assert len(ds_titles) == 0


@pytest.mark.usefixtures("clean_db")
class TestOrganizationMembership(object):
    def test_editor_users_cannot_add_members(self, app):

        user = factories.User()
        organization = factories.Organization(
            users=[{"name": user["name"], "capacity": "editor"}]
        )

        env = {"REMOTE_USER": user["name"].encode("ascii")}

        with app.flask_app.test_request_context():
            app.get(
                url_for("organization.member_new", id=organization["id"]),
                extra_environ=env,
                status=403,
            )

            app.post(
                url_for("organization.member_new", id=organization["id"]),
                {
                    "id": "test",
                    "username": "test",
                    "save": "save",
                    "role": "test",
                },
                extra_environ=env,
                status=403,
            )

    def test_member_users_cannot_add_members(self, app):
        user = factories.User()
        organization = factories.Organization(
            users=[{"name": user["name"], "capacity": "member"}]
        )

        env = {"REMOTE_USER": user["name"].encode("ascii")}

        with app.flask_app.test_request_context():
            app.get(
                url_for("organization.member_new", id=organization["id"]),
                extra_environ=env,
                status=403,
            )

            app.post(
                url_for("organization.member_new", id=organization["id"]),
                {
                    "id": "test",
                    "username": "test",
                    "save": "save",
                    "role": "test",
                },
                extra_environ=env,
                status=403,
            )

    def test_anonymous_users_cannot_add_members(self, app):
        organization = factories.Organization()

        with app.flask_app.test_request_context():
            app.get(
                url_for("organization.member_new", id=organization["id"]),
                status=403,
            )

            app.post(
                url_for("organization.member_new", id=organization["id"]),
                {
                    "id": "test",
                    "username": "test",
                    "save": "save",
                    "role": "test",
                },
                status=403,
            )


@pytest.mark.usefixtures("clean_db")
class TestActivity(object):
    def test_simple(self, app):
        """Checking the template shows the activity stream."""
        user = factories.User()
        org = factories.Organization(user=user)

        url = url_for("organization.activity", id=org["id"])
        response = app.get(url)
        assert "Mr. Test User" in response
        assert "created the organization" in response

    def test_create_organization(self, app):
        user = factories.User()
        org = factories.Organization(user=user)

        url = url_for("organization.activity", id=org["id"])
        response = app.get(url)
        assert (
            '<a href="/user/{}">Mr. Test User'.format(user["name"]) in response
        )
        assert "created the organization" in response
        assert (
            '<a href="/organization/{}">Test Organization'.format(org["name"])
            in response
        )

    def _clear_activities(self):
        model.Session.query(model.ActivityDetail).delete()
        model.Session.query(model.Activity).delete()
        model.Session.flush()

    def test_change_organization(self, app):
        user = factories.User()
        org = factories.Organization(user=user)
        self._clear_activities()
        org["title"] = "Organization with changed title"
        helpers.call_action(
            "organization_update", context={"user": user["name"]}, **org
        )

        url = url_for("organization.activity", id=org["id"])
        response = app.get(url)
        assert (
            '<a href="/user/{}">Mr. Test User'.format(user["name"]) in response
        )
        assert "updated the organization" in response
        assert (
            '<a href="/organization/{}">Organization with changed title'.format(
                org["name"]
            )
            in response
        )

    def test_delete_org_using_organization_delete(self, app):
        user = factories.User()
        org = factories.Organization(user=user)
        self._clear_activities()
        helpers.call_action(
            "organization_delete", context={"user": user["name"]}, **org
        )

        url = url_for("organization.activity", id=org["id"])
        env = {"REMOTE_USER": user["name"].encode("ascii")}
        response = app.get(url, extra_environ=env, status=404)
        # organization_delete causes the Member to state=deleted and then the
        # user doesn't have permission to see their own deleted Organization.
        # Therefore you can't render the activity stream of that org. You'd
        # hope that organization_delete was the same as organization_update
        # state=deleted but they are not...

    def test_delete_org_by_updating_state(self, app):
        user = factories.User()
        org = factories.Organization(user=user)
        self._clear_activities()
        org["state"] = "deleted"
        helpers.call_action(
            "organization_update", context={"user": user["name"]}, **org
        )

        url = url_for("organization.activity", id=org["id"])
        env = {"REMOTE_USER": user["name"].encode("ascii")}
        response = app.get(url, extra_environ=env)
        assert (
            '<a href="/user/{}">Mr. Test User'.format(user["name"]) in response
        )
        assert "deleted the organization" in response
        assert (
            '<a href="/organization/{}">Test Organization'.format(org["name"])
            in response
        )

    def test_create_dataset(self, app):
        user = factories.User()
        org = factories.Organization()
        self._clear_activities()
        dataset = factories.Dataset(owner_org=org["id"], user=user)

        url = url_for("organization.activity", id=org["id"])
        response = app.get(url)
        assert (
            '<a href="/user/{}">Mr. Test User'.format(user["name"]) in response
        )
        assert "created the dataset" in response
        assert (
            '<a href="/dataset/{}">Test Dataset'.format(dataset["id"])
            in response
        )

    def test_change_dataset(self, app):
        user = factories.User()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"], user=user)
        self._clear_activities()
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        url = url_for("organization.activity", id=org["id"])
        response = app.get(url)
        assert (
            '<a href="/user/{}">Mr. Test User'.format(user["name"]) in response
        )
        assert "updated the dataset" in response
        assert (
            '<a href="/dataset/{}">Dataset with changed title'.format(
                dataset["id"]
            )
            in response
        )

    def test_delete_dataset(self, app):
        user = factories.User()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"], user=user)
        self._clear_activities()
        helpers.call_action(
            "package_delete", context={"user": user["name"]}, **dataset
        )

        url = url_for("organization.activity", id=org["id"])
        response = app.get(url)
        assert (
            '<a href="/user/{}">Mr. Test User'.format(user["name"]) in response
        )
        assert "deleted the dataset" in response
        assert (
            '<a href="/dataset/{}">Test Dataset'.format(dataset["id"])
            in response
        )
