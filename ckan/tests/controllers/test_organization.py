# encoding: utf-8

import pytest
from bs4 import BeautifulSoup

import ckan.authz as authz
import ckan.model as model
from ckan.lib.helpers import url_for
from ckan.tests import factories, helpers


@pytest.fixture
def user():
    user = factories.UserWithToken()
    return user


@pytest.fixture
def sysadmin():
    user = factories.SysadminWithToken()
    return user


@pytest.mark.usefixtures("clean_db")
class TestOrganizationNew(object):

    def test_not_logged_in(self, app):
        app.get(url=url_for("group.new"), status=403)

    def test_name_required(self, app, user):
        url = url_for("organization.new")
        headers = {"Authorization": user["token"]}
        response = app.post(url=url, headers=headers, data={"save": ""})
        assert "Name: Missing value" in response

    def test_saved(self, app, user):
        headers = {"Authorization": user["token"]}
        url = url_for("organization.new")
        app.post(
            url=url, headers=headers, data={"save": "", "name": "saved"}
        )
        group = helpers.call_action("organization_show", id="saved")
        assert group["title"] == u""
        assert group["type"] == "organization"
        assert group["state"] == "active"

    def test_all_fields_saved(self, app, user):
        headers = {"Authorization": user["token"]}
        app.post(
            url=url_for("organization.new"),
            headers=headers,
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


class TestOrganizationList(object):
    @pytest.mark.usefixtures("non_clean_db")
    def test_error_message_shown_when_no_organization_list_permission(
        self, monkeypatch, app, user
    ):
        authz._AuthFunctions.get('organization_list')
        monkeypatch.setitem(
            authz._AuthFunctions._functions, 'organization_list',
            lambda *args: {'success': False}
        )
        self.organization_list_url = url_for("organization.index")
        headers = {"Authorization": user["token"]}
        app.get(
            url=self.organization_list_url,
            headers=headers,
            status=403
        )


@pytest.mark.usefixtures("non_clean_db")
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


@pytest.mark.usefixtures("non_clean_db")
class TestOrganizationEdit(object):

    def test_group_doesnt_exist(self, app, user):
        headers = {"Authorization": user["token"]}
        url = url_for("organization.edit", id="doesnt_exist")
        app.get(url=url, headers=headers, status=404)

    def test_saved(self, app, user):
        headers = {"Authorization": user["token"]}
        group = factories.Organization(user=user)
        app.post(
            url=url_for(
                "organization.edit", id=group["id"]
            ),
            headers=headers,
            data={"save": ""}
        )

        group = helpers.call_action(
            "organization_show", id=group["id"]
        )
        assert group["type"] == "organization"
        assert group["state"] == "active"

    def test_all_fields_saved(self, app, user):
        headers = {"Authorization": user["token"]}
        group = factories.Organization(user=user)
        app.post(
            url=url_for(
                "organization.edit", id=group["id"]
            ),
            headers=headers,
            data={
                "name": u"all-fields-edited",
                "title": "Science",
                "description": "Sciencey datasets",
                "image_url": "http://example.com/image.png",
                "save": ""
            }
        )
        group = helpers.call_action(
            "organization_show", id=group["id"]
        )
        assert group["title"] == u"Science"
        assert group["description"] == "Sciencey datasets"
        assert group["image_url"] == "http://example.com/image.png"


@pytest.mark.usefixtures("non_clean_db")
class TestOrganizationDelete(object):

    def test_owner_delete(self, app, user):
        headers = {"Authorization": user["token"]}
        group = factories.Organization(user=user)
        app.post(
            url=url_for(
                "organization.delete", id=group["id"]
            ),
            headers=headers,
            data={"delete": ""}
        )
        organization = helpers.call_action(
            "organization_show", id=group["id"]
        )
        assert organization["state"] == "deleted"

    def test_sysadmin_delete(self, app, sysadmin):
        group = factories.Organization()
        headers = {"Authorization": sysadmin["token"]}
        app.post(
            url=url_for(
                "organization.delete", id=group["id"]
            ),
            headers=headers,
            status=200,
            data={"delete": ""}
        )
        organization = helpers.call_action(
            "organization_show", id=group["id"]
        )
        assert organization["state"] == "deleted"

    def test_delete_form_rendered_correctly(self, app, sysadmin):
        group = factories.Organization()
        headers = {"Authorization": sysadmin["token"]}

        res = app.get(
            url=url_for(
                "organization.delete", id=group["id"]
            ),
            headers=headers,
            status=200
        )

        assert helpers.body_contains(res, url_for("organization.delete", id=group["id"]))

    def test_non_authorized_user_trying_to_delete_fails(
        self, app, user
    ):
        headers = {"Authorization": user["token"]}
        group = factories.Organization()
        app.post(
            url=url_for(
                "organization.delete", id=group["id"]
            ),
            headers=headers,
            status=403,
            data={"delete": ""}
        )

        organization = helpers.call_action(
            "organization_show", id=group["id"]
        )
        assert organization["state"] == "active"

    def test_anon_user_trying_to_delete_fails(self, app):
        group = factories.Organization()
        app.get(
            url=url_for(
                "organization.delete", id=group["id"]
            ),
            status=403,
        )

        organization = helpers.call_action(
            "organization_show", id=group["id"]
        )
        assert organization["state"] == "active"

    @pytest.mark.ckan_config("ckan.auth.create_unowned_dataset", False)
    def test_delete_organization_with_datasets(self, app, user):
        """ Test deletion of organization that has datasets"""
        headers = {"Authorization": user["token"]}
        group = factories.Organization(user=user)
        text = "Organization cannot be deleted while it still has datasets"
        for _ in range(0, 5):
            factories.Dataset(owner_org=group["id"])

        response = app.post(
            url=url_for(
                "organization.delete", id=group["id"]
            ),
            headers=headers,
            data={"delete": ""},
        )

        assert helpers.body_contains(response, text)

    def test_delete_organization_with_unknown_dataset_true(self, user):
        """ Test deletion of organization that has datasets and unknown
            datasets are set to true"""
        group = factories.Organization(user=user)
        dataset = factories.Dataset(
            owner_org=group["id"]
        )
        assert dataset["owner_org"] == group["id"]
        user = factories.User()
        helpers.call_action(
            "organization_delete",
            id=group["id"],
            context={"user": user["name"]},
        )

        dataset = helpers.call_action("package_show", id=dataset["id"])
        assert dataset["owner_org"] is None


@pytest.mark.usefixtures("non_clean_db")
class TestOrganizationBulkProcess(object):
    def test_make_private(self, app, user):
        headers = {"Authorization": user["token"]}
        self.organization = factories.Organization(user=user)

        datasets = [
            factories.Dataset(owner_org=self.organization["id"], private=False)
            for _ in range(0, 5)
        ]
        form = {'dataset_' + d["id"]: "on" for d in datasets}
        form["bulk_action.private"] = "private"

        app.post(
            url=url_for(
                "organization.bulk_process", id=self.organization["id"]
            ),
            headers=headers,
            data=form
        )

        for dataset in datasets:
            d = helpers.call_action("package_show", id=dataset["id"])
            assert d["private"]

    def test_make_public(self, app, user):
        headers = {"Authorization": user["token"]}
        self.organization = factories.Organization(user=user)

        datasets = [
            factories.Dataset(owner_org=self.organization["id"], private=True)
            for _ in range(0, 5)
        ]
        form = {'dataset_' + d["id"]: "on" for d in datasets}
        form["bulk_action.public"] = "public"
        app.post(
            url=url_for(
                "organization.bulk_process", id=self.organization["id"]
            ),
            headers=headers,
            data=form
        )
        for dataset in datasets:
            d = helpers.call_action("package_show", id=dataset["id"])
            assert not (d["private"])

    def test_delete(self, app, user):
        headers = {"Authorization": user["token"]}
        self.organization = factories.Organization(user=user)
        datasets = [
            factories.Dataset(owner_org=self.organization["id"], private=True)
            for _ in range(0, 5)
        ]
        form = {'dataset_' + d["id"]: "on" for d in datasets}
        form["bulk_action.delete"] = "delete"

        app.post(
            url=url_for(
                "organization.bulk_process", id=self.organization["id"]
            ),
            headers=headers,
            data=form
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


@pytest.mark.usefixtures("non_clean_db")
class TestOrganizationMembership(object):
    def test_editor_users_cannot_add_members(self, app, user):
        headers = {"Authorization": user["token"]}
        organization = factories.Organization(
            users=[{"name": user["name"], "capacity": "editor"}]
        )

        with app.flask_app.test_request_context():
            app.get(
                url_for("organization.member_new", id=organization["id"]),
                headers=headers,
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
                headers=headers,
                status=403,
            )

    def test_member_users_cannot_add_members(self, app, user):
        headers = {"Authorization": user["token"]}
        organization = factories.Organization(
            users=[{"name": user["name"], "capacity": "member"}]
        )

        with app.flask_app.test_request_context():
            app.get(
                url_for("organization.member_new", id=organization["id"]),
                headers=headers,
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
                headers=headers,
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

    @pytest.mark.usefixtures("with_request_context")
    def test_create_user_for_user_invite(self, mail_server, sysadmin):
        group = factories.Group()
        context = {"user": sysadmin["name"]}

        user_form = {
            "email": "user@ckan.org",
            "group_id": group["id"],
            "role": "member"
        }

        user_dict = helpers.call_action("user_invite", context, **user_form)
        user_obj = model.User.get(user_dict["id"])

        assert user_obj.password is None
        assert user_obj.state == 'pending'
        assert user_obj.last_active is None

    def test_member_delete(self, app, sysadmin, user):
        headers = {"Authorization": sysadmin["token"]}
        org = factories.Organization(
            users=[{"name": user["name"], "capacity": "member"}]
        )
        # our user + test.ckan.net
        assert len(org["users"]) == 2
        with app.flask_app.test_request_context():
            app.post(
                url_for("organization.member_delete", id=org["id"], user=user["id"]),
                headers=headers,
            )
            org = helpers.call_action('organization_show', id=org['id'])

            # only test.ckan.net
            assert len(org['users']) == 1
            assert user["id"] not in org["users"][0]["id"]


@pytest.mark.usefixtures("non_clean_db")
class TestOrganizationFollow:
    def test_organization_follow_and_unfollow(self, app, user):
        headers = {"Authorization": user["token"]}

        organization = factories.Organization()
        organization_url = url_for("organization.read", id=organization["id"])
        response = app.get(organization_url, headers=headers)
        assert '<a class="btn btn-success"' in response
        assert 'hx-target="#organization-info"' in response
        assert 'fa-circle-plus"></i> Follow' in response
        assert '''
            <dt>Followers</dt>
            <dd><span>0</span></dd>
          ''' in response

        follow_url = url_for("organization.follow", id=organization["id"])
        response = app.post(follow_url, headers=headers)
        assert '<a class="btn btn-danger"' in response
        assert 'hx-target="#organization-info"' in response
        assert 'fa-circle-minus"></i> Unfollow' in response
        assert '''
            <dt>Followers</dt>
            <dd><span>1</span></dd>
        ''' in response

    def test_organization_follow_not_exist(self, app, user):
        """Pass an id for a organization that doesn't exist"""

        headers = {"Authorization": user["token"]}
        follow_url = url_for("organization.follow", id="not-here")
        app.post(follow_url, headers=headers, status=404)

    def test_organization_unfollow(self, app, user):

        organization = factories.Organization()

        headers = {"Authorization": user["token"]}
        follow_url = url_for("organization.follow", id=organization["id"])
        app.post(follow_url, headers=headers)

        unfollow_url = url_for("organization.unfollow", id=organization["id"])
        response = app.post(unfollow_url, headers=headers)
        assert '<a class="btn btn-success"' in response
        assert 'hx-target="#organization-info"' in response
        assert 'fa-circle-plus"></i> Follow' in response
        assert '''
            <dt>Followers</dt>
            <dd><span>0</span></dd>
        ''' in response

    def test_organization_unfollow_not_following(self, app, user):
        """Unfollow a organization not currently following"""

        organization = factories.Organization()

        headers = {"Authorization": user["token"]}
        unfollow_url = url_for("organization.unfollow", id=organization["id"])
        response = app.post(unfollow_url, headers=headers)
        assert '<a class="btn btn-success"' in response
        assert 'hx-target="#organization-info"' in response
        assert 'fa-circle-plus"></i> Follow' in response
        assert '''
            <dt>Followers</dt>
            <dd><span>0</span></dd>
          ''' in response

    def test_organization_unfollow_not_exist(self, app, user):
        """Unfollow a organization that doesn't exist."""

        headers = {"Authorization": user["token"]}
        unfollow_url = url_for("organization.unfollow", id="not-here")
        app.post(unfollow_url, headers=headers, status=404)

    def test_organization_follower_list(self, app, sysadmin):
        """Following users appear on followers list page."""
        organization = factories.Organization()
        headers = {"Authorization": sysadmin["token"]}
        follow_url = url_for("organization.follow", id=organization["id"])
        app.post(follow_url, headers=headers)

        followers_url = url_for("organization.followers", id=organization["id"])

        # Only sysadmins can view the followers list pages
        followers_response = app.get(followers_url, headers=headers, status=200)
        assert sysadmin["name"] in followers_response
