# encoding: utf-8
import mock
import pytest
import six
from bs4 import BeautifulSoup

import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan import model
from ckan.lib.helpers import url_for
from ckan.lib.mailer import create_reset_key, MailerException


def _clear_activities():
    model.Session.query(model.ActivityDetail).delete()
    model.Session.query(model.Activity).delete()
    model.Session.flush()


def _get_user_edit_page(app):
    user = factories.User()
    env = {"REMOTE_USER": six.ensure_str(user["name"])}
    response = app.get(url=url_for("user.edit"), extra_environ=env)
    return env, response, user


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestUser(object):
    def test_register_a_user(self, app):
        url = url_for("user.register")
        response = app.post(url=url, data={
            "save": "",
            "name": "newuser",
            "fullname": "New User",
            "email": "test@test.com",
            "password1": "TestPassword1",
            "password2": "TestPassword1",
        })

        assert 200 == response.status_code

        user = helpers.call_action("user_show", id="newuser")
        assert user["name"] == "newuser"
        assert user["fullname"] == "New User"
        assert not (user["sysadmin"])

    def test_register_user_bad_password(self, app):
        response = app.post(url_for("user.register"), data={
            "save": "",
            "name": "newuser",
            "fullname": "New User",
            "email": "test@test.com",
            "password1": "TestPassword1",
            "password2": "",

        })
        assert "The passwords you entered do not match" in response

    def test_create_user_as_sysadmin(self, app):
        admin_pass = "RandomPassword123"
        sysadmin = factories.Sysadmin(password=admin_pass)

        # Have to do an actual login as this test relies on repoze
        #  cookie handling.

        # get the form
        response = app.post("/login_generic?came_from=/user/logged_in", data={
            "save": "",
            "login": sysadmin["name"],
            "password": admin_pass,

        })

        response = app.post(url_for("user.register"), data={
            "name": "newestuser",
            "fullname": "Newest User",
            "email": "test@test.com",
            "password1": "NewPassword1",
            "password2": "NewPassword1",
            "save": ""
        }, follow_redirects=False)

        assert "/user/activity" in response.headers['location']

    def test_registered_user_login(self, app):
        """
    Registered user can submit valid login details at /user/login and
    be returned to appropriate place.
    """
        # make a user
        user = factories.User()

        # get the form
        response = app.post("/login_generic?came_from=/user/logged_in", data={
            "login": user["name"],
            "password": "RandomPassword123",
        })
        # the response is the user dashboard, right?
        assert '<a href="/dashboard/">Dashboard</a>' in response
        assert '<span class="username">{0}</span>'.format(user["fullname"]) in response

        # and we're definitely not back on the login page.
        assert '<h1 class="page-heading">Login</h1>' not in response

    def test_registered_user_login_bad_password(self, app):
        """
    Registered user is redirected to appropriate place if they submit
    invalid login details at /user/login.
    """

        # make a user
        user = factories.User()

        # get the form
        response = app.post("/login_generic?came_from=/user/logged_in", data={
            "login": user["name"],
            "password": "BadPass1",
            "save": ""
        })

        # the response is the login page again
        assert '<h1 class="page-heading">Login</h1>' in response
        assert "Login failed. Bad username or password." in response
        # and we're definitely not on the dashboard.
        assert '<a href="/dashboard">Dashboard</a>' not in response
        assert '<span class="username">{0}</span>'.format(user["fullname"]) not in response

    def test_user_logout_url_redirect(self, app):
        """_logout url redirects to logged out page.

    Note: this doesn't test the actual logout of a logged in user, just
    the associated redirect.
    """

        logout_url = url_for("user.logout")
        final_response = app.get(logout_url)

        assert "You are now logged out." in final_response

    @pytest.mark.ckan_config("ckan.root_path", "/my/prefix")
    def test_non_root_user_logout_url_redirect(self, app):
        """
    _logout url redirects to logged out page with `ckan.root_path`
    prefixed.

    Note: this doesn't test the actual logout of a logged in user, just
    the associated redirect.
    """

        logout_url = url_for("user.logout")
        # Remove the prefix otherwise the test app won't find the correct route
        logout_url = logout_url.replace("/my/prefix", "")
        logout_response = app.get(logout_url, follow_redirects=False)
        assert logout_response.status_code == 302
        assert "/my/prefix/user/logout" in logout_response.headers['location']

    def test_not_logged_in_dashboard(self, app):
        for route in ["index", "organizations", "datasets", "groups"]:
            response = app.get(url=url_for(u"dashboard.{}".format(route)), follow_redirects=False)
            assert response.status_code == 302
            assert "user/login" in response.headers['location']

    def test_own_datasets_show_up_on_user_dashboard(self, app):
        user = factories.User()
        dataset_title = "My very own dataset"
        factories.Dataset(
            user=user, name="my-own-dataset", title=dataset_title
        )

        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        response = app.get(
            url=url_for("dashboard.datasets"), extra_environ=env
        )

        assert dataset_title in response

    def test_other_datasets_dont_show_up_on_user_dashboard(self, app):
        user1 = factories.User()
        user2 = factories.User()
        dataset_title = "Someone else's dataset"
        factories.Dataset(
            user=user1, name="someone-elses-dataset", title=dataset_title
        )

        env = {"REMOTE_USER": six.ensure_str(user2["name"])}
        response = app.get(
            url=url_for("dashboard.datasets"), extra_environ=env
        )

        assert not (dataset_title in response)

    def test_user_edit_no_user(self, app):

        response = app.get(url_for("user.edit", id=None), status=400)
        assert "No user specified" in response

    def test_user_edit_unknown_user(self, app):
        """Attempt to read edit user for an unknown user redirects to login
    page."""

        response = app.get(
            url_for("user.edit", id="unknown_person"), status=403
        )

    def test_user_edit_not_logged_in(self, app):
        """Attempt to read edit user for an existing, not-logged in user
    redirects to login page."""

        user = factories.User()
        username = user["name"]
        response = app.get(url_for("user.edit", id=username), status=403)

    def test_edit_user(self, app):
        user = factories.User(password="TestPassword1")

        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        response = app.post(url=url_for("user.edit"), extra_environ=env, data={
            "save": "",
            "name": user['name'],
            "fullname": "new full name",
            "email": "new@example.com",
            "about": "new about",
            "activity_streams_email_notifications": True,
            "old_password": "TestPassword1",
            "password1": "NewPass1",
            "password2": "NewPass1",
        })

        user = model.Session.query(model.User).get(user["id"])
        # assert(user.name== 'new-name')
        assert user.fullname == "new full name"
        assert user.email == "new@example.com"
        assert user.about == "new about"
        assert user.activity_streams_email_notifications

    def test_edit_user_as_wrong_user(self, app):
        user = factories.User(password="TestPassword1")
        other_user = factories.User(password="TestPassword2")

        env = {"REMOTE_USER": six.ensure_str(other_user["name"])}
        response = app.get(url_for("user.edit", id=user['name']), extra_environ=env, status=403)

    def test_email_change_without_password(self, app):

        user = factories.User()
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        response = app.post(url=url_for("user.edit"), extra_environ=env, data={
            "email": "new@example.com",
            "save": "",
            "old_password": "Wrong-pass1",
            "password1": "",
            "password2": "",
        })
        assert "Old Password: incorrect password" in response

    def test_email_change_with_password(self, app):

        user = factories.User()
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        response = app.post(url=url_for("user.edit"), extra_environ=env, data={
            "email": "new@example.com",
            "save": "",
            "old_password": "RandomPassword123",
            "password1": "",
            "password2": "",
            "name": user['name'],
        })
        assert "Profile updated" in response

    def test_email_change_on_existed_email(self, app):
        user1 = factories.User(email='existed@email.com')
        user2 = factories.User()
        env = {"REMOTE_USER": six.ensure_str(user2["name"])}

        response = app.post(url=url_for("user.edit"), extra_environ=env, data={
            "email": "existed@email.com",
            "save": "",
            "old_password": "RandomPassword123",
            "password1": "",
            "password2": "",
            "name": user2['name'],
        })
        assert 'belongs to a registered user' in response

    def test_edit_user_logged_in_username_change(self, app):

        user_pass = "TestPassword1"
        user = factories.User(password=user_pass)

        # Have to do an actual login as this test relys on repoze cookie handling.
        # get the form
        response = app.post("/login_generic?came_from=/user/logged_in", data={
            "login": user["name"],
            "password": user_pass,
            "save": ""
        })

        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        response = app.post(url=url_for("user.edit"), extra_environ=env, data={
            "email": user["email"],
            "save": "",
            "password1": "",
            "password2": "",
            "name": "new-name",
        })

        assert "That login name can not be modified" in response

    def test_edit_user_logged_in_username_change_by_name(self, app):
        user_pass = "TestPassword1"
        user = factories.User(password=user_pass)

        # Have to do an actual login as this test relys on repoze cookie handling.
        # get the form
        response = app.post("/login_generic?came_from=/user/logged_in", data={
            "login": user["name"],
            "password": user_pass,
            "save": ""
        })

        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        response = app.post(url=url_for("user.edit", id=user["name"]), extra_environ=env, data={
            "email": user["email"],
            "save": "",
            "password1": "",
            "password2": "",
            "name": "new-name",
        })

        assert "That login name can not be modified" in response

    def test_edit_user_logged_in_username_change_by_id(self, app):
        user_pass = "TestPassword1"
        user = factories.User(password=user_pass)

        # Have to do an actual login as this test relys on repoze cookie handling.
        # get the form
        response = app.post("/login_generic?came_from=/user/logged_in", data={
            "login": user["name"],
            "password": user_pass,
            "save": ""
        })

        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        response = app.post(url=url_for("user.edit", id=user["id"]), extra_environ=env, data={
            "email": user["email"],
            "save": "",
            "password1": "",
            "password2": "",
            "name": "new-name",
        })

        assert "That login name can not be modified" in response

    def test_perform_reset_for_key_change(self, app):
        password = "TestPassword1"
        params = {"password1": password, "password2": password}
        user = factories.User()
        user_obj = helpers.model.User.by_name(user["name"])
        create_reset_key(user_obj)
        key = user_obj.reset_key

        offset = url_for(
            controller="user",
            action="perform_reset",
            id=user_obj.id,
            key=user_obj.reset_key,
        )
        response = app.post(offset, data=params)
        user_obj = helpers.model.User.by_name(user["name"])  # Update user_obj

        assert key != user_obj.reset_key

    def test_password_reset_correct_password(self, app):
        """
    user password reset attempted with correct old password
    """

        user = factories.User()
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        response = app.post(url=url_for("user.edit"), extra_environ=env, data={
            "save": "",
            "old_password": "RandomPassword123",
            "password1": "NewPassword1",
            "password2": "NewPassword1",
            "name": user['name'],
            "email": user['email'],
        })

        assert "Profile updated" in response

    def test_password_reset_incorrect_password(self, app):
        """
    user password reset attempted with invalid old password
    """
        user = factories.User()
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        response = app.post(url=url_for("user.edit"), extra_environ=env, data={
            "save": "",
            "old_password": "Wrong-Pass1",
            "password1": "NewPassword1",
            "password2": "NewPassword1",
            "name": user['name'],
            "email": user['email'],
        })
        assert "Old Password: incorrect password" in response

    def test_user_follow(self, app):

        user_one = factories.User()
        user_two = factories.User()

        env = {"REMOTE_USER": six.ensure_str(user_one["name"])}
        follow_url = url_for(
            controller="user", action="follow", id=user_two["id"]
        )
        response = app.post(follow_url, extra_environ=env)
        assert (
            "You are now following {0}".format(user_two["display_name"])
            in response
        )

    def test_user_follow_not_exist(self, app):
        """Pass an id for a user that doesn't exist"""

        user_one = factories.User()

        env = {"REMOTE_USER": six.ensure_str(user_one["name"])}
        follow_url = url_for(controller="user", action="follow", id="not-here")
        response = app.post(follow_url, extra_environ=env)

        assert response.status_code == 404

    def test_user_unfollow(self, app):

        user_one = factories.User()
        user_two = factories.User()

        env = {"REMOTE_USER": six.ensure_str(user_one["name"])}
        follow_url = url_for(
            controller="user", action="follow", id=user_two["id"]
        )
        app.post(follow_url, extra_environ=env)

        unfollow_url = url_for("user.unfollow", id=user_two["id"])
        unfollow_response = app.post(
            unfollow_url, extra_environ=env
        )

        assert (
            "You are no longer following {0}".format(user_two["display_name"])
            in unfollow_response
        )

    def test_user_unfollow_not_following(self, app):
        """Unfollow a user not currently following"""

        user_one = factories.User()
        user_two = factories.User()

        env = {"REMOTE_USER": six.ensure_str(user_one["name"])}
        unfollow_url = url_for("user.unfollow", id=user_two["id"])
        unfollow_response = app.post(
            unfollow_url, extra_environ=env
        )

        assert (
            "You are not following {0}".format(user_two["id"])
            in unfollow_response
        )

    def test_user_unfollow_not_exist(self, app):
        """Unfollow a user that doesn't exist."""

        user_one = factories.User()

        env = {"REMOTE_USER": six.ensure_str(user_one["name"])}
        unfollow_url = url_for(
            controller="user", action="unfollow", id="not-here")
        response = app.post(unfollow_url, extra_environ=env)

        assert response.status_code == 404

    def test_user_follower_list(self, app):
        """Following users appear on followers list page."""

        user_one = factories.Sysadmin()
        user_two = factories.User()

        env = {"REMOTE_USER": six.ensure_str(user_one["name"])}
        follow_url = url_for(
            controller="user", action="follow", id=user_two["id"]
        )
        app.post(follow_url, extra_environ=env)

        followers_url = url_for("user.followers", id=user_two["id"])

        # Only sysadmins can view the followers list pages
        followers_response = app.get(
            followers_url, extra_environ=env, status=200
        )
        assert user_one["display_name"] in followers_response

    def test_user_page_anon_access(self, app):
        """Anon users can access the user list page"""

        user_url = url_for("user.index")
        user_response = app.get(user_url, status=200)
        assert "<title>All Users - CKAN</title>" in user_response

    def test_user_page_lists_users(self, app):
        """/users/ lists registered users"""
        initial_user_count = model.User.count()
        factories.User(fullname="User One")
        factories.User(fullname="User Two")
        factories.User(fullname="User Three")

        user_url = url_for("user.index")
        user_response = app.get(user_url, status=200)

        user_response_html = BeautifulSoup(user_response.data)
        user_list = user_response_html.select("ul.user-list li")
        assert len(user_list) == 3 + initial_user_count

        user_names = [u.text.strip() for u in user_list]
        assert "User One" in user_names
        assert "User Two" in user_names
        assert "User Three" in user_names

    def test_user_page_doesnot_list_deleted_users(self, app):
        """/users/ doesn't list deleted users"""
        initial_user_count = model.User.count()

        factories.User(fullname="User One", state="deleted")
        factories.User(fullname="User Two")
        factories.User(fullname="User Three")

        user_url = url_for("user.index")
        user_response = app.get(user_url, status=200)

        user_response_html = BeautifulSoup(user_response.data)
        user_list = user_response_html.select("ul.user-list li")
        assert len(user_list) == 2 + initial_user_count

        user_names = [u.text.strip() for u in user_list]
        assert "User One" not in user_names
        assert "User Two" in user_names
        assert "User Three" in user_names

    def test_user_page_anon_search(self, app):
        """Anon users can search for users by username."""

        factories.User(fullname="User One", email="useroneemail@example.com")
        factories.User(fullname="Person Two")
        factories.User(fullname="Person Three")

        user_url = url_for("user.index")
        search_response = app.get(user_url, query_string={'q': "Person"})

        search_response_html = BeautifulSoup(search_response.data)
        user_list = search_response_html.select("ul.user-list li")
        assert len(user_list) == 2

        user_names = [u.text.strip() for u in user_list]
        assert "Person Two" in user_names
        assert "Person Three" in user_names
        assert "User One" not in user_names

    def test_user_page_anon_search_not_by_email(self, app):
        """Anon users can not search for users by email."""

        factories.User(fullname="User One", email="useroneemail@example.com")
        factories.User(fullname="Person Two")
        factories.User(fullname="Person Three")

        user_url = url_for("user.index")
        search_response = app.get(user_url, query_string={'q': "useroneemail@example.com"})

        search_response_html = BeautifulSoup(search_response.data)
        user_list = search_response_html.select("ul.user-list li")
        assert len(user_list) == 0

    def test_user_page_sysadmin_user(self, app):
        """Sysadmin can search for users by email."""

        sysadmin = factories.Sysadmin()

        factories.User(fullname="User One", email="useroneemail@example.com")
        factories.User(fullname="Person Two")
        factories.User(fullname="Person Three")

        env = {"REMOTE_USER": six.ensure_str(sysadmin["name"])}
        user_url = url_for("user.index")
        search_response = app.get(user_url, query_string={'q': "useroneemail@example.com"}, extra_environ=env)

        search_response_html = BeautifulSoup(search_response.data)
        user_list = search_response_html.select("ul.user-list li")
        assert len(user_list) == 1
        assert user_list[0].text.strip() == "User One"

    def test_simple(self, app):
        """Checking the template shows the activity stream."""

        user = factories.User()

        url = url_for("user.activity", id=user["id"])
        response = app.get(url)
        assert "Mr. Test User" in response
        assert "signed up" in response

    def test_create_user(self, app):

        user = factories.User()

        url = url_for("user.activity", id=user["id"])
        response = app.get(url)
        assert (
            '<a href="/user/{}">Mr. Test User'.format(user["name"]) in response
        )
        assert "signed up" in response

    def test_change_user(self, app):

        user = factories.User()
        _clear_activities()
        user["fullname"] = "Mr. Changed Name"
        helpers.call_action(
            "user_update", context={"user": user["name"]}, **user
        )

        url = url_for("user.activity", id=user["id"])
        response = app.get(url)
        assert (
            '<a href="/user/{}">Mr. Changed Name'.format(user["name"])
            in response
        )
        assert "updated their profile" in response

    def test_create_dataset(self, app):

        user = factories.User()
        _clear_activities()
        dataset = factories.Dataset(user=user)

        url = url_for("user.activity", id=user["id"])
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
        dataset = factories.Dataset(user=user)
        _clear_activities()
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update", context={"user": user["name"]}, **dataset
        )

        url = url_for("user.activity", id=user["id"])
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
        dataset = factories.Dataset(user=user)
        _clear_activities()
        helpers.call_action(
            "package_delete", context={"user": user["name"]}, **dataset
        )

        url = url_for("user.activity", id=user["id"])
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        response = app.get(url, extra_environ=env)
        assert (
            '<a href="/user/{}">Mr. Test User'.format(user["name"]) in response
        )
        assert "deleted the dataset" in response
        assert (
            '<a href="/dataset/{}">Test Dataset'.format(dataset["id"])
            in response
        )

    def test_create_group(self, app):

        user = factories.User()
        group = factories.Group(user=user)

        url = url_for("user.activity", id=user["id"])
        response = app.get(url)
        assert (
            '<a href="/user/{}">Mr. Test User'.format(user["name"]) in response
        )
        assert "created the group" in response
        assert '<a href="/group/{}">Test Group'.format(group["id"]) in response

    def test_change_group(self, app):

        user = factories.User()
        group = factories.Group(user=user)
        _clear_activities()
        group["title"] = "Group with changed title"
        helpers.call_action(
            "group_update", context={"user": user["name"]}, **group
        )

        url = url_for("user.activity", id=user["id"])
        response = app.get(url)
        assert (
            '<a href="/user/{}">Mr. Test User'.format(user["name"]) in response
        )
        assert "updated the group" in response
        assert (
            '<a href="/group/{}">Group with changed title'.format(group["id"])
            in response
        )

    def test_delete_group_using_group_delete(self, app):

        user = factories.User()
        group = factories.Group(user=user)
        _clear_activities()
        helpers.call_action(
            "group_delete", context={"user": user["name"]}, **group
        )

        url = url_for("user.activity", id=user["id"])
        response = app.get(url)
        assert (
            '<a href="/user/{}">Mr. Test User'.format(user["name"]) in response
        )
        assert "deleted the group" in response
        assert '<a href="/group/{}">Test Group'.format(group["id"]) in response

    def test_delete_group_by_updating_state(self, app):

        user = factories.User()
        group = factories.Group(user=user)
        _clear_activities()
        group["state"] = "deleted"
        helpers.call_action(
            "group_update", context={"user": user["name"]}, **group
        )

        url = url_for("group.activity", id=group["id"])
        env = {"REMOTE_USER": six.ensure_str(user["name"])}
        response = app.get(url, extra_environ=env)
        assert (
            '<a href="/user/{}">Mr. Test User'.format(user["name"]) in response
        )
        assert "deleted the group" in response
        assert (
            '<a href="/group/{}">Test Group'.format(group["name"]) in response
        )

    @mock.patch("ckan.lib.mailer.send_reset_link")
    def test_request_reset_by_email(self, send_reset_link, app):
        user = factories.User()

        offset = url_for("user.request_reset")
        response = app.post(
            offset, data=dict(user=user["email"])
        )

        assert "A reset link has been emailed to you" in response
        assert send_reset_link.call_args[0][0].id == user["id"]

    @mock.patch("ckan.lib.mailer.send_reset_link")
    def test_request_reset_by_name(self, send_reset_link, app):
        user = factories.User()

        offset = url_for("user.request_reset")
        response = app.post(
            offset, data=dict(user=user["name"])
        )

        assert "A reset link has been emailed to you" in response
        assert send_reset_link.call_args[0][0].id == user["id"]

    def test_request_reset_without_param(self, app):

        offset = url_for("user.request_reset")
        response = app.post(offset)

        assert "Email is required" in response

    @mock.patch("ckan.lib.mailer.send_reset_link")
    def test_request_reset_for_unknown_username(self, send_reset_link, app):

        offset = url_for("user.request_reset")
        response = app.post(
            offset, data=dict(user="unknown")
        )

        # doesn't reveal account does or doesn't exist
        assert "A reset link has been emailed to you" in response
        send_reset_link.assert_not_called()

    @mock.patch("ckan.lib.mailer.send_reset_link")
    def test_request_reset_for_unknown_email(self, send_reset_link, app):

        offset = url_for("user.request_reset")
        response = app.post(
            offset, data=dict(user="unknown@example.com")
        )

        # doesn't reveal account does or doesn't exist
        assert "A reset link has been emailed to you" in response
        send_reset_link.assert_not_called()

    @mock.patch("ckan.lib.mailer.send_reset_link")
    def test_request_reset_but_mailer_not_configured(
        self, send_reset_link, app
    ):
        user = factories.User()

        offset = url_for("user.request_reset")
        # This is the exception when the mailer is not configured:
        send_reset_link.side_effect = MailerException(
            'SMTP server could not be connected to: "localhost" '
            "[Errno 111] Connection refused"
        )
        response = app.post(
            offset, data=dict(user=user["name"])
        )

        assert "Error sending the email" in response


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestUserImage(object):

    def test_image_url_is_shown(self, app):

        user = factories.User(image_url='https://example.com/mypic.png')

        url = url_for('user.read', id=user['name'])

        res = app.get(url, extra_environ={'REMOTE_USER': user['name']})

        res_html = BeautifulSoup(res.data)
        user_images = res_html.select('img.user-image')

        assert len(user_images) == 2    # Logged in header + profile pic
        for img in user_images:
            assert img.attrs['src'] == 'https://example.com/mypic.png'

    def test_fallback_to_gravatar(self, app):

        user = factories.User(image_url=None)

        url = url_for('user.read', id=user['name'])

        res = app.get(url, extra_environ={'REMOTE_USER': user['name']})

        res_html = BeautifulSoup(res.data)
        user_images = res_html.select('img.user-image')

        assert len(user_images) == 2    # Logged in header + profile pic
        for img in user_images:
            assert img.attrs['src'].startswith('//gravatar')

    @pytest.mark.ckan_config('ckan.gravatar_default', 'disabled')
    def test_fallback_to_placeholder_if_gravatar_disabled(self, app):

        user = factories.User(image_url=None)

        url = url_for('user.read', id=user['name'])

        res = app.get(url, extra_environ={'REMOTE_USER': user['name']})

        res_html = BeautifulSoup(res.data)
        user_images = res_html.select('img.user-image')

        assert len(user_images) == 2    # Logged in header + profile pic
        for img in user_images:
            assert img.attrs['src'] == '/base/images/placeholder-user.png'
