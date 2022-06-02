# encoding: utf-8

import pytest
import six
from bs4 import BeautifulSoup

import ckan.authz as authz
from ckan.lib.helpers import url_for
from ckan.tests import factories, helpers


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestOrganizationNew(object):
    @pytest.fixture
    def user_env(self):
        user = factories.User()
        return {"REMOTE_USER": six.ensure_str(user["name"])}

    def test_not_logged_in(self, app):
        app.get(url=url_for("group.new"), status=403)

    def test_name_required(self, app, user_env):
        response = app.post(
            url=url_for("organization.new"), extra_environ=user_env, data={"save": ""}
        )
        assert "Name: Missing value" in response

    def test_saved(self, app, user_env):
        app.post(
            url=url_for("organization.new"), extra_environ=user_env,
            data={"save": "", "name": "saved"}
        )
        group = helpers.call_action("organization_show", id="saved")
        assert group["title"] == u""
        assert group["type"] == "organization"
        assert group["state"] == "active"

    def test_all_fields_saved(self, app, user_env):
        app.post(
            url=url_for("organization.new"), extra_environ=user_env,
            data={
                "name": u"all-fields-saved",
                "title": "Science",
                "description": "Sciencey datasets",
                "image_url": "http://example.com/image.png",
                "save": ""
            }
        )
        group = helpers.call_action("organization_show", id="all-fields-saved")
        assert group["title"] == u"Science"
        assert group["description"] == "Sciencey datasets"


@pytest.mark.usefixtures("with_request_context")
class TestOrganizationList(object):
    @pytest.mark.usefixtures("non_clean_db")
    def test_error_message_shown_when_no_organization_list_permission(
        self, monkeypatch, app
    ):
        authz._AuthFunctions.get('organization_list')
        monkeypatch.setitem(
            authz._AuthFunctions._functions, 'organization_list',
            lambda *args: {'success': False})
        self.user = factories.User()
        self.user_env = {"REMOTE_USER": six.ensure_str(self.user["name"])}
        self.organization_list_url = url_for("organization.index")

        app.get(
            url=self.organization_list_url,
            extra_environ=self.user_env,
            status=403,
        )


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestOrganizationRead(object):
    def test_group_read(self, app):
        org = factories.Organization()
        response = app.get(url=url_for("organization.read", id=org["name"]))
        assert org["title"] in response
        assert org["description"] in response

    def test_read_redirect_when_given_id(self, app):
        org = factories.Organization()
        response = app.get(
            url_for("organization.read", id=org["id"]), follow_redirects=False
        )
        # redirect replaces the ID with the name in the URL
        expected_url = url_for("organization.read", id=org["name"], _external=True)
        assert response.headers['location'] == expected_url

    def test_no_redirect_loop_when_name_is_the_same_as_the_id(self, app):
        name = factories.Organization.stub().name
        org = factories.Organization(id=name, name=name)
        app.get(
            url_for("organization.read", id=org["id"]), status=200
        )  # ie no redirect


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestOrganizationEdit(object):
    @pytest.fixture
    def initial_data(self):
        user = factories.User()
        return {
            "user": user,
            "user_env": {"REMOTE_USER": six.ensure_str(user["name"])},
            "organization": factories.Organization(user=user),
        }

    def test_group_doesnt_exist(self, app, initial_data):
        url = url_for("organization.edit", id="doesnt_exist")
        app.get(url=url, extra_environ=initial_data["user_env"], status=404)

    def test_saved(self, app, initial_data):
        app.post(
            url=url_for(
                "organization.edit", id=initial_data["organization"]["id"]
            ),
            extra_environ=initial_data["user_env"],
            data={"save": ""}
        )

        group = helpers.call_action(
            "organization_show", id=initial_data["organization"]["id"]
        )
        assert group["type"] == "organization"
        assert group["state"] == "active"

    def test_all_fields_saved(self, app, initial_data):
        app.post(
            url=url_for(
                "organization.edit", id=initial_data["organization"]["id"]
            ),
            extra_environ=initial_data["user_env"],
            data={
                "name": u"all-fields-edited",
                "title": "Science",
                "description": "Sciencey datasets",
                "image_url": "http://example.com/image.png",
                "save": ""
            }
        )
        group = helpers.call_action(
            "organization_show", id=initial_data["organization"]["id"]
        )
        assert group["title"] == u"Science"
        assert group["description"] == "Sciencey datasets"
        assert group["image_url"] == "http://example.com/image.png"


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestOrganizationDelete(object):
    @pytest.fixture
    def initial_data(self):
        user = factories.User()
        return {
            "user": user,
            "user_env": {"REMOTE_USER": six.ensure_str(user["name"])},
            "organization": factories.Organization(user=user),
        }

    def test_owner_delete(self, app, initial_data):
        app.post(
            url=url_for(
                "organization.delete", id=initial_data["organization"]["id"]
            ),
            extra_environ=initial_data["user_env"],
            data={"delete": ""}
        )
        organization = helpers.call_action(
            "organization_show", id=initial_data["organization"]["id"]
        )
        assert organization["state"] == "deleted"

    def test_sysadmin_delete(self, app, initial_data):
        sysadmin = factories.Sysadmin()
        extra_environ = {"REMOTE_USER": six.ensure_str(sysadmin["name"])}
        app.post(
            url=url_for(
                "organization.delete", id=initial_data["organization"]["id"]
            ),
            status=200,
            extra_environ=extra_environ,
            data={"delete": ""}
        )
        organization = helpers.call_action(
            "organization_show", id=initial_data["organization"]["id"]
        )
        assert organization["state"] == "deleted"

    def test_non_authorized_user_trying_to_delete_fails(
        self, app, initial_data
    ):
        user = factories.User()
        extra_environ = {"REMOTE_USER": six.ensure_str(user["name"])}
        app.post(
            url=url_for(
                "organization.delete", id=initial_data["organization"]["id"]
            ),
            status=403,
            extra_environ=extra_environ,
            data={"delete": ""}
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
        for i in range(0, 5):
            factories.Dataset(owner_org=initial_data["organization"]["id"])

        response = app.post(
            url=url_for(
                "organization.delete", id=initial_data["organization"]["id"]
            ),
            extra_environ=initial_data["user_env"],
            data={"delete": ""}
        )

        assert helpers.body_contains(response, text)

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


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestOrganizationBulkProcess(object):
    def test_make_private(self, app):
        self.user = factories.User()
        self.user_env = {"REMOTE_USER": six.ensure_str(self.user["name"])}
        self.organization = factories.Organization(user=self.user)

        datasets = [
            factories.Dataset(owner_org=self.organization["id"], private=False)
            for i in range(0, 5)
        ]
        form = {'dataset_' + d["id"]: "on" for d in datasets}
        form["bulk_action.private"] = "private"

        app.post(
            url=url_for(
                "organization.bulk_process", id=self.organization["id"]
            ),
            extra_environ=self.user_env,
            data=form
        )

        for dataset in datasets:
            d = helpers.call_action("package_show", id=dataset["id"])
            assert d["private"]

    def test_make_public(self, app):
        self.user = factories.User()
        self.user_env = {"REMOTE_USER": six.ensure_str(self.user["name"])}
        self.organization = factories.Organization(user=self.user)

        datasets = [
            factories.Dataset(owner_org=self.organization["id"], private=True)
            for i in range(0, 5)
        ]
        form = {'dataset_' + d["id"]: "on" for d in datasets}
        form["bulk_action.public"] = "public"
        app.post(
            url=url_for(
                "organization.bulk_process", id=self.organization["id"]
            ),
            extra_environ=self.user_env,
            data=form
        )
        for dataset in datasets:
            d = helpers.call_action("package_show", id=dataset["id"])
            assert not (d["private"])

    def test_delete(self, app):
        self.user = factories.User()
        self.user_env = {"REMOTE_USER": six.ensure_str(self.user["name"])}
        self.organization = factories.Organization(user=self.user)
        datasets = [
            factories.Dataset(owner_org=self.organization["id"], private=True)
            for i in range(0, 5)
        ]
        form = {'dataset_' + d["id"]: "on" for d in datasets}
        form["bulk_action.delete"] = "delete"

        app.post(
            url=url_for(
                "organization.bulk_process", id=self.organization["id"]
            ),
            extra_environ=self.user_env,

            data=form
        )

        for dataset in datasets:
            d = helpers.call_action("package_show", id=dataset["id"])
            assert d["state"] == "deleted"


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestOrganizationSearch(object):
    """Test searching for organizations."""

    def test_organization_search(self, app):
        """Requesting organization search (index) returns list of
        organizations and search form."""

        factories.Organization(title="AOrg One")
        factories.Organization(title="AOrg Two")
        factories.Organization(title="Org Three")

        index_response = app.get(url_for("organization.index"))
        index_response_html = BeautifulSoup(index_response.body)
        org_names = index_response_html.select(
            "ul.media-grid " "li.media-item " "h2.media-heading"
        )
        org_names = [n.string for n in org_names]

        assert len(org_names) == 3
        assert "AOrg One" in org_names
        assert "AOrg Two" in org_names
        assert "Org Three" in org_names

    def test_organization_search_results(self, app):
        """Searching via organization search form returns list of expected
        organizations."""
        factories.Organization(title="AOrg One")
        factories.Organization(title="AOrg Two")
        factories.Organization(title="Org Three")

        search_response = app.get(
            url_for("organization.index"),
            query_string={"q": "AOrg"}
        )

        search_response_html = BeautifulSoup(search_response.body)
        org_names = search_response_html.select(
            "ul.media-grid " "li.media-item " "h2.media-heading"
        )
        org_names = [n.string for n in org_names]

        assert len(org_names) == 2
        assert "AOrg One" in org_names
        assert "AOrg Two" in org_names
        assert "Org Three" not in org_names

    def test_organization_search_no_results(self, app):
        """Searching with a term that doesn't apply returns no results."""
        factories.Organization(title="AOrg One")
        factories.Organization(title="AOrg Two")
        factories.Organization(title="Org Three")

        search_response = app.get(
            url_for("organization.index"),
            query_string={"q": "No Results Here"}
        )

        search_response_html = BeautifulSoup(search_response.body)
        org_names = search_response_html.select(
            "ul.media-grid " "li.media-item " "h2.media-heading"
        )
        org_names = [n.string for n in org_names]

        assert len(org_names) == 0
        assert helpers.body_contains(
            search_response,
            'No organizations found for "No Results Here"'
        )


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestOrganizationInnerSearch(object):
    """Test searching within an organization."""

    def test_organization_search_within_org(self, app):
        """Organization read page request returns list of datasets owned by
        organization."""
        org = factories.Organization()
        factories.Dataset(
            title="Dataset One", owner_org=org["id"]
        )
        factories.Dataset(
            title="Dataset Two", owner_org=org["id"]
        )
        factories.Dataset(
            title="Dataset Three", owner_org=org["id"]
        )

        org_url = url_for("organization.read", id=org["name"])
        org_response = app.get(org_url)
        org_response_html = BeautifulSoup(org_response.body)

        ds_titles = org_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        ds_titles = [t.string.strip() for t in ds_titles]

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
            title="Dataset One", owner_org=org["id"]
        )
        factories.Dataset(
            title="Dataset Two", owner_org=org["id"]
        )
        factories.Dataset(
            title="Dataset Three", owner_org=org["id"]
        )

        org_url = url_for("organization.read", id=org["name"])
        search_response = app.get(
            org_url,
            query_string={"q": "One"}
        )
        assert "1 dataset found" in search_response

        search_response_html = BeautifulSoup(search_response.body)

        ds_titles = search_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        ds_titles = [t.string.strip() for t in ds_titles]

        assert len(ds_titles) == 1
        assert "Dataset One" in ds_titles
        assert "Dataset Two" not in ds_titles
        assert "Dataset Three" not in ds_titles

    def test_organization_search_within_org_no_results(self, app):
        """Searching for non-returning phrase within an organization returns
        no results."""

        org = factories.Organization()
        factories.Dataset(
            title="Dataset One", owner_org=org["id"]
        )
        factories.Dataset(
            title="Dataset Two", owner_org=org["id"]
        )
        factories.Dataset(
            title="Dataset Three", owner_org=org["id"]
        )

        org_url = url_for("organization.read", id=org["name"])
        search_response = app.get(
            org_url,
            query_string={"q": "Nout"}
        )

        assert helpers.body_contains(search_response, 'No datasets found for "Nout"')

        search_response_html = BeautifulSoup(search_response.body)

        ds_titles = search_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        ds_titles = [t.string for t in ds_titles]

        assert len(ds_titles) == 0


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestOrganizationMembership(object):
    def test_editor_users_cannot_add_members(self, app):

        user = factories.User()
        organization = factories.Organization(
            users=[{"name": user["name"], "capacity": "editor"}]
        )

        env = {"REMOTE_USER": six.ensure_str(user["name"])}

        with app.flask_app.test_request_context():
            app.get(
                url_for("organization.member_new", id=organization["id"]),
                extra_environ=env,
                status=403,
            )

            app.post(
                url_for("organization.member_new", id=organization["id"]),
                data={
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

        env = {"REMOTE_USER": six.ensure_str(user["name"])}

        with app.flask_app.test_request_context():
            app.get(
                url_for("organization.member_new", id=organization["id"]),
                extra_environ=env,
                status=403,
            )

            app.post(
                url_for("organization.member_new", id=organization["id"]),
                data={
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
                data={
                    "id": "test",
                    "username": "test",
                    "save": "save",
                    "role": "test",
                },
                status=403,
            )

    def test_member_delete(self, app):
        sysadmin = factories.Sysadmin()
        user = factories.User()
        org = factories.Organization(
            users=[{"name": user["name"], "capacity": "member"}]
        )
        env = {"REMOTE_USER": six.ensure_str(sysadmin["name"])}
        # our user + test.ckan.net
        assert len(org["users"]) == 2
        with app.flask_app.test_request_context():
            app.post(
                url_for("organization.member_delete", id=org["id"], user=user["id"]),
                extra_environ=env,
            )
            org = helpers.call_action('organization_show', id=org['id'])

            # only test.ckan.net
            assert len(org['users']) == 1
            assert user["id"] not in org["users"][0]["id"]
