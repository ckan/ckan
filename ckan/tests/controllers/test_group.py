# encoding: utf-8

import unittest.mock as mock
from bs4 import BeautifulSoup
import pytest
from ckan.lib.helpers import url_for
import ckan.logic as logic
import ckan.tests.helpers as helpers
import ckan.model as model
from ckan.tests import factories


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestGroupController(object):
    def test_bulk_process_throws_403_for_nonexistent_org(self, app):
        """Returns 403, not 404, because access check cannot be passed.
        """
        bulk_process_url = url_for(
            "organization.bulk_process", id="does-not-exist"
        )
        app.get(url=bulk_process_url, status=403)

    def test_page_thru_list_of_orgs_preserves_sort_order(self, app):
        orgs = sorted([factories.Organization() for _ in range(35)],
                      key=lambda o: o["name"])
        org_url = url_for("organization.index", sort="name desc")
        response = app.get(url=org_url)
        assert orgs[-1]["name"] in response
        assert orgs[0]["name"] not in response

        org_url = url_for("organization.index", sort="name desc", page=2)
        response = app.get(url=org_url)
        assert orgs[-1]["name"] not in response
        assert orgs[0]["name"] in response

    def test_page_thru_list_of_groups_preserves_sort_order(self, app):
        groups = sorted([factories.Group() for _ in range(35)],
                        key=lambda g: g["title"])
        group_url = url_for("group.index", sort="title desc")

        response = app.get(url=group_url)
        assert groups[-1]["title"] in response
        assert groups[0]["title"] not in response

        org_url = url_for("group.index", sort="title desc", page=2)
        response = app.get(url=org_url)
        assert groups[-1]["title"] not in response
        assert groups[0]["title"] in response

    def test_invalid_sort_param_does_not_crash(self, app):

        with app.flask_app.test_request_context():
            group_url = url_for("group.index", sort="title desc nope")

            app.get(url=group_url)

            group_url = url_for("group.index", sort="title nope desc nope")

            app.get(url=group_url)


@pytest.fixture
def sysadmin():
    user = factories.SysadminWithToken()
    return user


@pytest.fixture
def user():
    user = factories.UserWithToken()
    return user


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestGroupControllerNew(object):
    def test_not_logged_in(self, app):
        app.get(url=url_for("group.new"), status=403)

    def test_name_required(self, app, user):
        env = {"Authorization": user["token"]}
        url = url_for("group.new")
        response = app.post(url=url, extra_environ=env, data={"save": ""})

        assert "Name: Missing value" in response

    def test_saved(self, app, user):
        env = {"Authorization": user["token"]}
        form = {"name": "saved", "save": ""}
        url = url_for("group.new")
        app.post(url=url, extra_environ=env, data=form)

        group = model.Group.by_name(u"saved")
        assert group.title == u""
        assert group.type == "group"
        assert group.state == "active"

    def test_all_fields_saved(self, app, user):
        form = {
            "name": u"all-fields-saved",
            "title": "Science",
            "description": "Sciencey datasets",
            "image_url": "http://example.com/image.png",
            "save": "",
        }
        env = {"Authorization": user["token"]}
        url = url_for("group.new")
        app.post(url=url, extra_environ=env, data=form)

        group = model.Group.by_name(u"all-fields-saved")
        assert group.title == u"Science"
        assert group.description == "Sciencey datasets"

    def test_form_without_initial_data(self, app, user):
        url = url_for("group.new")
        env = {"Authorization": user["token"]}
        resp = app.get(url=url, extra_environ=env)
        page = BeautifulSoup(resp.body)
        form = page.select_one('#group-edit')
        assert not form.select_one('[name=title]')['value']
        assert not form.select_one('[name=name]')['value']
        assert not form.select_one('[name=description]').text

    def test_form_with_initial_data(self, app, user):
        url = url_for("group.new", name="name",
                      description="description", title="title")
        env = {"Authorization": user["token"]}
        resp = app.get(url=url, extra_environ=env)
        page = BeautifulSoup(resp.body)
        form = page.select_one('#group-edit')
        assert form.select_one('[name=title]')['value'] == "title"
        assert form.select_one('[name=name]')['value'] == "name"
        assert form.select_one('[name=description]').text == "description"


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestGroupControllerEdit(object):
    def test_not_logged_in(self, app):
        app.get(url=url_for("group.new"), status=403)

    def test_group_doesnt_exist(self, app, user):
        env = {"Authorization": user["token"]}
        url = url_for("group.edit", id="doesnt_exist")
        app.get(url=url, extra_environ=env, status=404)

    def test_saved(self, app, user):
        env = {"Authorization": user["token"]}
        group = factories.Group(user=user)
        url = url_for("group.edit", id=group["name"])
        form = {"save": ""}
        app.post(url=url, extra_environ=env, data=form)
        group = model.Group.by_name(group["name"])
        assert group.state == "active"

    def test_all_fields_saved(self, app, user):
        env = {"Authorization": user["token"]}
        group = factories.Group(user=user)

        form = {
            "name": u"all-fields-edited",
            "title": "Science",
            "description": "Sciencey datasets",
            "image_url": "http://example.com/image.png",
            "save": "",
        }
        url = url_for("group.edit", id=group["name"])
        app.post(url=url, extra_environ=env, data=form)

        group = model.Group.by_name(u"all-fields-edited")
        assert group.title == u"Science"
        assert group.description == "Sciencey datasets"
        assert group.image_url == "http://example.com/image.png"

    def test_display_name_shown(self, app, user):
        env = {"Authorization": user["token"]}
        group = factories.Group(
            title="Display name",
            user=user
        )

        form = {
            "name": "",
            "save": "",
        }
        url = url_for("group.edit", id=group["name"])
        resp = app.get(url=url, extra_environ=env)
        page = BeautifulSoup(resp.body)
        breadcrumbs = page.select('.breadcrumb a')
        # Home -> Groups -> NAME -> Manage
        assert len(breadcrumbs) == 4
        # Verify that `NAME` is not empty, as well as other parts
        assert all([part.text for part in breadcrumbs])
        url = url_for("group.edit", id=group["name"])
        resp = app.post(url=url, extra_environ=env, data=form)
        page = BeautifulSoup(resp.body)
        breadcrumbs = page.select('.breadcrumb a')
        # Home -> Groups -> NAME -> Manage
        assert len(breadcrumbs) == 4
        # Verify that `NAME` is not empty, as well as other parts
        assert all([part.text for part in breadcrumbs])


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestGroupRead(object):
    def test_group_read(self, app):
        group = factories.Group()
        response = app.get(url=url_for("group.read", id=group["name"]))
        assert group["title"] in response
        assert group["description"] in response

    def test_redirect_when_given_id(self, app):
        group = factories.Group()

        response = app.get(
            url_for("group.read", id=group["id"]),
            status=302,
            follow_redirects=False,
        )
        location = response.headers["location"]
        expected_url = url_for("group.read", id=group["name"], _external=True)
        assert location == expected_url

    def test_no_redirect_loop_when_name_is_the_same_as_the_id(self, app):
        name = factories.Group.stub().name
        group = factories.Group(id=name, name=name)

        # 200 == no redirect
        app.get(url_for("group.read", id=group["id"]), status=200)

    def test_search_with_extra_params(self, app):
        group = factories.Group()
        url = url_for('group.read', id=group['id'])
        url += '?ext_a=1&ext_a=2&ext_b=3'
        search_result = {
            'count': 0,
            'sort': "score desc, metadata_modified desc",
            'facets': {},
            'search_facets': {},
            'results': []
        }
        search = mock.Mock(return_value=search_result)
        logic._actions['package_search'] = search
        app.get(url)
        search.assert_called()
        extras = search.call_args[0][1]['extras']
        assert extras == {'ext_a': ['1', '2'], 'ext_b': '3'}


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestGroupDelete(object):

    def test_owner_delete(self, app, user):
        env = {"Authorization": user["token"]}
        group = factories.Group(user=user)
        response = app.post(
            url=url_for("group.delete", id=group["id"]),
            extra_environ=env,
            data={"delete": ""}
        )
        assert response.status_code == 200
        group = helpers.call_action(
            "group_show", id=group["id"]
        )
        assert group["state"] == "deleted"

    def test_sysadmin_delete(self, app, sysadmin):
        env = {"Authorization": sysadmin["token"]}
        group = factories.Group()
        response = app.post(
            url=url_for("group.delete", id=group["id"]),
            extra_environ=env,
            data={"delete": ""}
        )
        assert response.status_code == 200
        group = helpers.call_action(
            "group_show", id=group["id"]
        )
        assert group["state"] == "deleted"

    def test_non_authorized_user_trying_to_delete_fails(
        self, app, user
    ):
        env = {"Authorization": user["token"]}
        group = factories.Group()
        app.get(
            url=url_for("group.delete", id=group["id"]),
            extra_environ=env,
            status=403,
        )

        group = helpers.call_action(
            "group_show", id=group["id"]
        )
        assert group["state"] == "active"

    def test_anon_user_trying_to_delete_fails(self, app):
        group = factories.Group()
        app.get(
            url=url_for("group.delete", id=group["id"]),
            status=403,
        )

        group = helpers.call_action(
            "group_show", id=group["id"]
        )
        assert group["state"] == "active"


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestGroupMembership(object):
    def _create_group(self, owner_username, users=None):
        """Create a group with the owner defined by owner_username and
        optionally with a list of other users."""
        if users is None:
            users = []
        context = {"user": owner_username, "ignore_auth": True}
        group = helpers.call_action(
            "group_create", context=context, name=factories.Group.stub().name, users=users
        )
        return group

    def test_membership_list(self, app):
        """List group admins and members"""
        user_one = factories.User(fullname="User One")
        user_two = factories.User(fullname="User Two")
        user_one_token = factories.APIToken(user=user_one["name"])
        env = {"Authorization": user_one_token["token"]}

        other_users = [{"name": user_two["id"], "capacity": "member"}]

        group = self._create_group(user_one["name"], other_users)

        member_list_url = url_for("group.members", id=group["id"])

        member_list_response = app.get(member_list_url, extra_environ=env)

        assert "2 members" in member_list_response

        member_response_html = BeautifulSoup(member_list_response.body)
        user_names = [
            u.string
            for u in member_response_html.select("#member-table td.media a")
        ]
        roles = [
            r.next_sibling.next_sibling.string
            for r in member_response_html.select("#member-table td.media")
        ]

        user_roles = dict(zip(user_names, roles))

        assert user_roles["User One"] == "Admin"
        assert user_roles["User Two"] == "Member"

    def test_membership_add(self, app):
        """Member can be added via add member page"""
        user = factories.User(fullname="My Owner")
        factories.User(fullname="My Fullname", name="my-new-user")
        group = self._create_group(user["name"])

        url = url_for("group.member_new", id=group["name"])
        add_response = app.post(
            url,
            environ_overrides={"REMOTE_USER": user["name"]},
            data={"save": "", "username": "my-new-user", "role": "member"},
        )

        assert "2 members" in add_response.body

        add_response_html = BeautifulSoup(add_response.body)
        user_names = [
            u.string
            for u in add_response_html.select("#member-table td.media a")
        ]
        roles = [
            r.next_sibling.next_sibling.string
            for r in add_response_html.select("#member-table td.media")
        ]

        user_roles = dict(zip(user_names, roles))

        assert user_roles["My Owner"] == "Admin"
        assert user_roles["My Fullname"] == "Member"

    def test_membership_add_by_email(self, app, mail_server):
        user = factories.User(fullname="My Owner")
        group = self._create_group(user["name"])

        url = url_for("group.member_new", id=group["name"])
        email = "invited_user@mailinator.com"
        app.post(
            url,
            environ_overrides={"REMOTE_USER": user["name"]},
            data={"save": "", "email": email, "role": "member"},
            status=200
        )
        assert len(mail_server.get_smtp_messages()) == 1
        user = model.User.by_email(email)
        assert user.email == email
        assert group["id"] in user.get_group_ids(capacity="member")

    def test_membership_edit_page(self, app):
        """If `user` parameter provided, render edit page."""
        owner = factories.User(fullname="My Owner")
        member = factories.User(fullname="My Fullname", name="my-user")
        group = self._create_group(owner["name"], users=[
            {'name': member['name'], 'capacity': 'admin'}
        ])

        url = url_for("group.member_new", id=group["name"], user=member['name'])
        response = app.get(
            url,
            environ_overrides={"REMOTE_USER": owner["name"]},
        )

        page = BeautifulSoup(response.body)
        assert page.select_one('.page-heading').text.strip() == 'Edit Member'
        role_option = page.select_one('#role [selected]')
        assert role_option and role_option.get('value') == 'admin'
        assert page.select_one('#username').get('value') == member['name']

    @pytest.mark.usefixtures("clean_db")
    def test_admin_add(self, app):
        """Admin can be added via add member page"""
        owner = factories.User(fullname="My Owner")
        factories.User(fullname="My Fullname", name="my-admin-user")
        group = self._create_group(owner["name"])

        url = url_for("group.member_new", id=group["name"])
        add_response = app.post(
            url,
            environ_overrides={"REMOTE_USER": owner["name"]},
            data={"save": "", "username": "my-admin-user", "role": "admin"},
        )

        assert "2 members" in add_response

        add_response_html = BeautifulSoup(add_response.body)
        user_names = [
            u.string
            for u in add_response_html.select("#member-table td.media a")
        ]
        roles = [
            r.next_sibling.next_sibling.string
            for r in add_response_html.select("#member-table td.media")
        ]

        user_roles = dict(zip(user_names, roles))

        assert user_roles["My Owner"] == "Admin"
        assert user_roles["My Fullname"] == "Admin"

    def test_remove_member(self,  app):
        """Member can be removed from group"""
        user = factories.User(fullname="My Owner")
        user_two = factories.User(fullname="User Two")

        other_users = [{"name": user_two["id"], "capacity": "member"}]

        group = self._create_group(user["name"], other_users)

        remove_url = url_for(
            "group.member_delete", user=user_two["id"], id=group["id"]
        )

        remove_response = app.post(
            remove_url,
            environ_overrides={"REMOTE_USER": user["name"]},
        )
        assert helpers.body_contains(remove_response, "1 members")

        remove_response_html = BeautifulSoup(remove_response.body)
        user_names = [
            u.string
            for u in remove_response_html.select("#member-table td.media a")
        ]
        roles = [
            r.next_sibling.next_sibling.string
            for r in remove_response_html.select("#member-table td.media")
        ]

        user_roles = dict(zip(user_names, roles))

        assert len(user_roles.keys()) == 1
        assert user_roles["My Owner"] == "Admin"

    def test_member_users_cannot_add_members(self, app):
        user = factories.User(fullname="My Owner")
        group = factories.Group(
            users=[{"name": user["name"], "capacity": "member"}]
        )

        app.get(
            url_for("group.member_new", id=group["id"]),
            environ_overrides={"REMOTE_USER": user["name"]},
            status=403
        )

        app.post(
            url_for("group.member_new", id=group["id"]),
            environ_overrides={"REMOTE_USER": user["name"]},
            data={
                "id": "test",
                "username": "test",
                "save": "save",
                "role": "test",
            },
            status=403,
        )

    def test_anonymous_users_cannot_add_members(self, app):
        group = factories.Group()

        with app.flask_app.test_request_context():
            url = url_for("group.member_new", id=group["id"])
            app.get(url, status=403)

            app.post(
                url,
                data={
                    "id": "test",
                    "username": "test",
                    "save": "save",
                    "role": "test",
                },
                status=403,
            )


@pytest.mark.usefixtures("non_clean_db", "with_request_context")
class TestGroupFollow:
    def test_group_follow(self, app, user):

        group = factories.Group()

        env = {"Authorization": user["token"]}
        follow_url = url_for("group.follow", id=group["id"])
        response = app.post(follow_url, extra_environ=env)
        assert (
            "You are now following {0}".format(group["display_name"])
            in response
        )

    def test_group_follow_not_exist(self, app, user):
        """Pass an id for a group that doesn't exist"""

        env = {"Authorization": user["token"]}
        follow_url = url_for("group.follow", id="not-here")
        response = app.post(follow_url, extra_environ=env, status=404)
        assert "Group not found" in response

    def test_group_unfollow(self, app, user):

        group = factories.Group()

        env = {"Authorization": user["token"]}
        follow_url = url_for("group.follow", id=group["id"])
        app.post(follow_url, extra_environ=env)

        unfollow_url = url_for("group.unfollow", id=group["id"])
        unfollow_response = app.post(unfollow_url, extra_environ=env)

        assert (
            "You are no longer following {0}".format(group["display_name"])
            in unfollow_response
        )

    def test_group_unfollow_not_following(self, app, user):
        """Unfollow a group not currently following"""

        group = factories.Group()

        env = {"Authorization": user["token"]}
        unfollow_url = url_for("group.unfollow", id=group["id"])
        unfollow_response = app.post(unfollow_url, extra_environ=env)

        assert (
            "You are not following {0}".format(group["id"])
            in unfollow_response
        )

    def test_group_unfollow_not_exist(self, app, user):
        """Unfollow a group that doesn't exist."""

        env = {"Authorization": user["token"]}
        unfollow_url = url_for("group.unfollow", id="not-here")
        app.post(unfollow_url, extra_environ=env, status=404)

    def test_group_follower_list(self, app, sysadmin):
        """Following users appear on followers list page."""
        group = factories.Group()
        env = {"Authorization": sysadmin["token"]}
        follow_url = url_for("group.follow", id=group["id"])
        app.post(follow_url, extra_environ=env)

        followers_url = url_for("group.followers", id=group["id"])

        # Only sysadmins can view the followers list pages
        followers_response = app.get(followers_url, extra_environ=env, status=200)
        assert sysadmin["name"] in followers_response


@pytest.mark.usefixtures("clean_db", "clean_index", "with_request_context")
class TestGroupSearch(object):
    """Test searching for groups."""

    def test_group_search(self, app):
        """Requesting group search (index) returns list of groups and search
        form."""

        factories.Group(title="AGrp One")
        factories.Group(title="AGrp Two")
        factories.Group(title="Grp Three")
        index_response = app.get(url_for("group.index"))
        index_response_html = BeautifulSoup(index_response.body)
        grp_names = index_response_html.select(
            "ul.media-grid " "li.media-item " "h2.media-heading"
        )
        grp_names = [n.string for n in grp_names]

        assert len(grp_names) == 3
        assert "AGrp One" in grp_names
        assert "AGrp Two" in grp_names
        assert "Grp Three" in grp_names

    def test_group_search_results(self, app):
        """Searching via group search form returns list of expected groups."""
        factories.Group(title="AGrp One")
        factories.Group(title="AGrp Two")
        factories.Group(title="Grp Three")

        search_response = app.get(
            url_for("group.index"), query_string={"q": "AGrp"}
        )
        search_response_html = BeautifulSoup(search_response.body)
        grp_names = search_response_html.select(
            "ul.media-grid " "li.media-item " "h2.media-heading"
        )
        grp_names = [n.string for n in grp_names]

        assert len(grp_names) == 2
        assert "AGrp One" in grp_names
        assert "AGrp Two" in grp_names
        assert "Grp Three" not in grp_names

    def test_group_search_no_results(self, app):
        """Searching with a term that doesn't apply returns no results."""

        factories.Group(title="AGrp One")
        factories.Group(title="AGrp Two")
        factories.Group(title="Grp Three")

        search_response = app.get(
            url_for("group.index"), query_string={"q": "No Results Here"}
        )

        search_response_html = BeautifulSoup(search_response.body)
        grp_names = search_response_html.select(
            "ul.media-grid " "li.media-item " "h2.media-heading"
        )
        grp_names = [n.string for n in grp_names]

        assert len(grp_names) == 0
        assert 'No groups found for "No Results Here"' in search_response


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestGroupInnerSearch(object):
    """Test searching within an group."""

    def test_group_search_within_org(self, app):
        """Group read page request returns list of datasets owned by group."""
        grp = factories.Group()
        factories.Dataset(
            title="Dataset One", groups=[{"id": grp["id"]}]
        )
        factories.Dataset(
            title="Dataset Two", groups=[{"id": grp["id"]}]
        )
        factories.Dataset(
            title="Dataset Three", groups=[{"id": grp["id"]}]
        )

        grp_url = url_for("group.read", id=grp["name"])
        grp_response = app.get(grp_url)
        grp_response_html = BeautifulSoup(grp_response.body)

        ds_titles = grp_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        ds_titles = [t.string.strip() for t in ds_titles]

        assert "3 datasets found" in grp_response
        assert len(ds_titles) == 3
        assert "Dataset One" in ds_titles
        assert "Dataset Two" in ds_titles
        assert "Dataset Three" in ds_titles

    def test_group_search_within_org_results(self, app):
        """Searching within an group returns expected dataset results."""

        grp = factories.Group()
        factories.Dataset(
            title="Dataset One", groups=[{"id": grp["id"]}]
        )
        factories.Dataset(
            title="Dataset Two", groups=[{"id": grp["id"]}]
        )
        factories.Dataset(
            title="Dataset Three", groups=[{"id": grp["id"]}]
        )

        grp_url = url_for("group.read", id=grp["name"])

        search_response = app.get(grp_url, query_string={"q": "One"})
        assert "1 dataset found for &#34;One&#34;" in search_response

        search_response_html = BeautifulSoup(search_response.body)

        ds_titles = search_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        ds_titles = [t.string.strip() for t in ds_titles]

        assert len(ds_titles) == 1
        assert "Dataset One" in ds_titles
        assert "Dataset Two" not in ds_titles
        assert "Dataset Three" not in ds_titles

    def test_group_search_within_org_no_results(self, app):
        """Searching for non-returning phrase within an group returns no
        results."""

        grp = factories.Group()
        factories.Dataset(
            title="Dataset One", groups=[{"id": grp["id"]}]
        )
        factories.Dataset(
            title="Dataset Two", groups=[{"id": grp["id"]}]
        )
        factories.Dataset(
            title="Dataset Three", groups=[{"id": grp["id"]}]
        )

        grp_url = url_for("group.read", id=grp["name"])
        search_response = app.get(grp_url, query_string={"q": "Nout"})

        assert helpers.body_contains(
            search_response, 'No datasets found for "Nout"'
        )

        search_response_html = BeautifulSoup(search_response.body)

        ds_titles = search_response_html.select(
            ".dataset-list " ".dataset-item " ".dataset-heading a"
        )
        ds_titles = [t.string for t in ds_titles]

        assert len(ds_titles) == 0


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestGroupIndex(object):
    def test_group_index(self, app):

        for i in range(1, 26):
            _i = "0" + str(i) if i < 10 else i
            factories.Group(
                name="test-group-{0}".format(_i),
                title="Test Group {0}".format(_i),
            )

        url = url_for("group.index")
        response = app.get(url)

        for i in range(1, 21):
            _i = "0" + str(i) if i < 10 else i
            assert "Test Group {0}".format(_i) in response

        assert "Test Group 21" not in response

        url = url_for("group.index", page=1)
        response = app.get(url)

        for i in range(1, 21):
            _i = "0" + str(i) if i < 10 else i
            assert "Test Group {0}".format(_i) in response

        assert "Test Group 21" not in response

        url = url_for("group.index", page=2)
        response = app.get(url)

        for i in range(21, 26):
            assert "Test Group {0}".format(i) in response

        assert "Test Group 20" not in response
