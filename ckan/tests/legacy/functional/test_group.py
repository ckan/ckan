# encoding: utf-8

import pytest
import mock

import ckan.model as model

from ckan.lib.create_test_data import CreateTestData
from ckan.logic import get_action
from ckan.lib.helpers import url_for
import ckan.tests.factories as factories


@pytest.mark.usefixtures("clean_db", "clean_index", "with_request_context")
def test_sorting():
    testsysadmin = factories.Sysadmin(name=u"testsysadmin")

    pkg1 = model.Package(name="pkg1")
    pkg2 = model.Package(name="pkg2")
    model.Session.add(pkg1)
    model.Session.add(pkg2)

    CreateTestData.create_groups(
        [
            {"name": "alpha", "title": "Alpha", "packages": []},
            {"name": "beta", "title": "Beta", "packages": ["pkg1", "pkg2"]},
            {"name": "delta", "title": "Delta", "packages": ["pkg1"]},
            {"name": "gamma", "title": "Gamma", "packages": []},
        ],
        admin_user_name="testsysadmin",
    )

    context = {
        "model": model,
        "session": model.Session,
        "user": "testsysadmin",
        "for_view": True,
        "with_private": False,
    }
    data_dict = {"all_fields": True}
    results = get_action("group_list")(context, data_dict)
    assert results[0]["name"] == u"alpha", results[0]["name"]
    assert results[-1]["name"] == u"gamma", results[-1]["name"]

    # Test title forward
    data_dict = {"all_fields": True, "sort": "title asc"}
    results = get_action("group_list")(context, data_dict)
    assert results[0]["name"] == u"alpha", results[0]["name"]
    assert results[-1]["name"] == u"gamma", results[-1]["name"]

    # Test title reverse
    data_dict = {"all_fields": True, "sort": "title desc"}
    results = get_action("group_list")(context, data_dict)
    assert results[0]["name"] == u"gamma", results[0]["name"]
    assert results[-1]["name"] == u"alpha", results[-1]["name"]

    # Test name reverse
    data_dict = {"all_fields": True, "sort": "name desc"}
    results = get_action("group_list")(context, data_dict)
    assert results[0]["name"] == u"gamma", results[0]["name"]
    assert results[-1]["name"] == u"alpha", results[-1]["name"]

    # Test packages reversed
    data_dict = {"all_fields": True, "sort": "package_count desc"}
    results = get_action("group_list")(context, data_dict)
    assert results[0]["name"] == u"beta", results[0]["name"]
    assert results[1]["name"] == u"delta", results[1]["name"]

    # Test packages forward
    data_dict = {"all_fields": True, "sort": "package_count asc"}
    results = get_action("group_list")(context, data_dict)
    assert results[-2]["name"] == u"delta", results[-2]["name"]
    assert results[-1]["name"] == u"beta", results[-1]["name"]

    # Default ordering for packages
    data_dict = {"all_fields": True, "sort": "package_count"}
    results = get_action("group_list")(context, data_dict)
    assert results[0]["name"] == u"beta", results[0]["name"]
    assert results[1]["name"] == u"delta", results[1]["name"]


@pytest.mark.usefixtures("clean_db")
def test_read_non_existent(app):
    name = u"group_does_not_exist"
    offset = url_for(controller="group", action="read", id=name)
    app.get(offset, status=404)


@pytest.mark.usefixtures("clean_db", "with_request_context")
@mock.patch("ckan.lib.mailer.mail_user")
def test_member_new_invites_user_if_received_email(_mail_user, app):
    user = CreateTestData.create_user("a_user", sysadmin=True)
    group_name = "a_group"
    CreateTestData.create_groups([{"name": group_name}], user.name)
    group = model.Group.get(group_name)
    url = url_for(controller="group", action="member_new", id=group.id)
    email = "invited_user@mailinator.com"
    role = "member"

    params = {"email": email, "role": role}
    app.post(url, data=params, extra_environ={"REMOTE_USER": str(user.name)})

    users = model.User.by_email(email)
    assert len(users) == 1, users
    user = users[0]
    assert user.email == email, user
    assert group.id in user.get_group_ids(capacity=role)
