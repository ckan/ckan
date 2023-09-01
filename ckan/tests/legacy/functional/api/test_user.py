# encoding: utf-8


from __future__ import print_function
import ckan.logic as logic
from ckan import model
from ckan.lib.create_test_data import CreateTestData
from ckan.tests.legacy import TestController as ControllerTestCase
from ckan.tests.legacy import url_for
from ckan.tests import helpers
import pytest
from ckan.common import json


class TestUserApi(ControllerTestCase):
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db):
        CreateTestData.create()

    def test_autocomplete(self):
        response = self.app.get(
            url=url_for(controller="api", action="user_autocomplete", ver=2),
            params={"q": u"sysadmin"},
            status=200,
        )
        assert set(response.json[0].keys()) == set(["id", "name", "fullname"])
        assert response.json[0]["name"] == u"testsysadmin"
        assert (
            response.headers.get("Content-Type")
            == "application/json;charset=utf-8"
        )

    def test_autocomplete_multiple(self):
        response = self.app.get(
            url=url_for(controller="api", action="user_autocomplete", ver=2),
            params={"q": u"tes"},
            status=200,
        )
        assert len(response.json) == 2

    def test_autocomplete_limit(self):
        response = self.app.get(
            url=url_for(controller="api", action="user_autocomplete", ver=2),
            params={"q": u"tes", "limit": 1},
            status=200,
        )
        print(response.json)
        assert len(response.json) == 1


class TestCreateUserApiDisabled(object):
    """
    Tests for the creating user when create_user_via_api is disabled.
    """

    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db):
        CreateTestData.create()
        self.sysadmin_user = model.User.get("testsysadmin")

    def test_user_create_api_enabled_sysadmin(self, app):
        params = {
            "name": "testinganewusersysadmin",
            "email": "testinganewuser@ckan.org",
            "password": "TestPassword1",
        }
        res = app.post(
            "/api/3/action/user_create",
            json=params,
            extra_environ={"Authorization": str(self.sysadmin_user.apikey)},
        )
        res_dict = res.json
        assert res_dict["success"] is True

    def test_user_create_api_disabled_anon(self, app):
        params = {
            "name": "testinganewuseranon",
            "email": "testinganewuser@ckan.org",
            "password": "TestPassword1",
        }
        res = app.post(
            "/api/3/action/user_create", json=params
        )
        res_dict = res.json
        assert res_dict["success"] is False


class TestCreateUserApiEnabled(object):
    """
    Tests for the creating user when create_user_via_api is enabled.
    """

    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db):
        CreateTestData.create()
        self.sysadmin_user = model.User.get("testsysadmin")

    def test_user_create_api_enabled_sysadmin(self, app):
        params = {
            "name": "testinganewusersysadmin",
            "email": "testinganewuser@ckan.org",
            "password": "TestPassword1",
        }
        res = app.post(
            "/api/3/action/user_create",
            json=params,
            extra_environ={"Authorization": str(self.sysadmin_user.apikey)},
        )
        res_dict = res.json
        assert res_dict["success"] is True

    @pytest.mark.ckan_config("ckan.auth.create_user_via_api", True)
    def test_user_create_api_enabled_anon(self, app):
        params = {
            "name": "testinganewuseranon",
            "email": "testinganewuser@ckan.org",
            "password": "TestPassword1",
        }
        res = app.post("/api/3/action/user_create", json=params)
        res_dict = res.json
        assert res_dict["success"] is True


class TestCreateUserWebDisabled(object):
    """
    Tests for the creating user by create_user_via_web is disabled.
    """

    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db):
        CreateTestData.create()
        self.sysadmin_user = model.User.get("testsysadmin")

    @pytest.mark.ckan_config("ckan.auth.create_user_via_web", False)
    def test_user_create_api_disabled(self, app):
        params = {
            "name": "testinganewuser",
            "email": "testinganewuser@ckan.org",
            "password": "TestPassword1",
        }
        res = app.post(
            "/api/3/action/user_create", json=params
        )
        res_dict = res.json
        assert res_dict["success"] is False


class TestCreateUserWebEnabled(object):
    """
    Tests for the creating user by create_user_via_web is enabled.
    """

    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db):
        CreateTestData.create()
        self.sysadmin_user = model.User.get("testsysadmin")

    @pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
    def test_user_create_api_disabled(self, app):
        params = {
            "name": "testinganewuser",
            "email": "testinganewuser@ckan.org",
            "password": "TestPassword1",
        }
        res = app.post(
            "/api/3/action/user_create", json=params
        )
        res_dict = res.json
        assert res_dict["success"] is False


@pytest.mark.usefixtures("with_request_context")
class TestUserActions(object):
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db):
        CreateTestData.create()

    @pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
    def test_user_create_simple(self):
        """Simple creation of a new user by a non-sysadmin user."""
        context = {"model": model, "session": model.Session, "user": "tester"}
        data_dict = {
            "name": "a-new-user",
            "email": "a.person@example.com",
            "password": "TestPassword1",
        }

        user_dict = logic.get_action("user_create")(context, data_dict)

        assert user_dict["name"] == "a-new-user"
        assert "email" in user_dict
        assert "apikey" in user_dict
        assert "password" not in user_dict
