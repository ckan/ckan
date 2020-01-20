# encoding: utf-8

import pytest

import ckan.model as model
from ckan.lib.helpers import url_for
from ckan.lib.mailer import create_reset_key
from ckan.tests.legacy import CreateTestData


@pytest.fixture(autouse=True)
def initial_data(clean_db):

    CreateTestData.create()

    # make 3 changes, authored by annafan
    for i in range(3):
        pkg = model.Package.by_name(u"annakarenina")
        pkg.notes = u"Changed notes %i" % i
        model.repo.commit_and_remove()

    CreateTestData.create_user(
        "unfinisher", about='<a href="http://unfinished.tag'
    )
    CreateTestData.create_user(
        "uncloser", about='<a href="http://unclosed.tag">'
    )
    CreateTestData.create_user(
        "spammer",
        about=u'<a href="http://mysite">mysite</a> <a href=\u201dhttp://test2\u201d>test2</a>',
    )
    CreateTestData.create_user(
        "spammer2",
        about=u'<a href="http://spamsite1.com\u201d>spamsite1</a>\r\n<a href="http://www.spamsite2.com\u201d>spamsite2</a>\r\n',
    )


def test_user_delete_redirects_to_user_index(app):
    user = CreateTestData.create_user("a_user")
    url = url_for("user.delete", id=user.id)
    extra_environ = {"REMOTE_USER": "testsysadmin"}

    redirect_url = url_for("user.index", qualified=True)
    res = app.post(url, extra_environ=extra_environ, follow_redirects=False)

    assert user.is_deleted(), user
    assert res.headers["Location"].startswith(
        redirect_url
    )


def test_user_delete_by_unauthorized_user(app):
    user = model.User.by_name(u"annafan")
    url = url_for("user.delete", id=user.id)
    extra_environ = {"REMOTE_USER": "an_unauthorized_user"}

    app.post(url, status=403, extra_environ=extra_environ)


def test_user_read_without_id(app):
    offset = "/user/"
    app.get(offset, status=200)


def test_user_read_me_without_id(app):
    offset = "/user/me"
    app.get(offset, status=302, follow_redirects=False)


def test_apikey(app):
    username = u"okfntest"
    user = model.User.by_name(u"okfntest")
    if not user:
        user = model.User(name=u"okfntest")
        model.Session.add(user)
        model.Session.commit()
        model.Session.remove()

    # not logged in
    offset = url_for("user.read", id=username)
    res = app.get(offset)
    assert not "API key" in res

    offset = url_for("user.read", id="okfntest")
    res = app.get(offset, extra_environ={"REMOTE_USER": "okfntest"})
    assert user.apikey in res, res


def test_perform_reset_user_password_link_key_incorrect(app):
    CreateTestData.create_user(name="jack", password="TestPassword1")
    # Make up a key - i.e. trying to hack this
    user = model.User.by_name(u"jack")
    offset = url_for(
        controller="user", action="perform_reset", id=user.id, key="randomness"
    )  # i.e. incorrect
    res = app.get(offset, status=403)  # error


def test_perform_reset_user_password_link_key_missing(app):
    CreateTestData.create_user(name="jack", password="TestPassword1")
    user = model.User.by_name(u"jack")
    offset = url_for(
        controller="user", action="perform_reset", id=user.id
    )  # not, no key specified
    res = app.get(offset, status=403)  # error


def test_perform_reset_user_password_link_user_incorrect(app):
    # Make up a key - i.e. trying to hack this
    user = model.User.by_name(u"jack")
    offset = url_for(
        controller="user",
        action="perform_reset",
        id="randomness",  # i.e. incorrect
        key="randomness",
    )
    res = app.get(offset, status=404)


def test_perform_reset_activates_pending_user(app):
    password = "TestPassword1"
    params = {"password1": password, "password2": password}
    user = CreateTestData.create_user(
        name="pending_user", email="user@email.com"
    )
    user.set_pending()
    create_reset_key(user)
    assert user.is_pending(), user.state

    offset = url_for(
        controller="user",
        action="perform_reset",
        id=user.id,
        key=user.reset_key,
    )
    res = app.post(offset, params=params)

    user = model.User.get(user.id)
    assert user.is_active(), user


def test_perform_reset_doesnt_activate_deleted_user(app):
    password = "TestPassword1"
    params = {"password1": password, "password2": password}
    user = CreateTestData.create_user(
        name="deleted_user", email="user@email.com"
    )
    user.delete()
    create_reset_key(user)
    assert user.is_deleted(), user.state

    offset = url_for(
        controller="user",
        action="perform_reset",
        id=user.id,
        key=user.reset_key,
    )
    res = app.post(offset, params=params, status=403)

    user = model.User.get(user.id)
    assert user.is_deleted(), user
