# -*- coding: utf-8 -*-

from unittest import mock
from flask_login import user_logged_in as signals_user_logged_in
import pytest

import ckan.model as model

from ckan.lib import mailer, signals
from ckan.tests import factories
from ckan.lib.helpers import url_for


@pytest.mark.ckan_config(u"ckan.plugins", u"example_idatasetform_v6")
def test_register_blueprint(make_app):
    receiver = mock.Mock()
    with signals.register_blueprint.connected_to(receiver):
        make_app()
    assert receiver.call_count == 2
    (type_,), _ = receiver.call_args_list[0]
    assert type_ == u"dataset"

    (type_,), _ = receiver.call_args_list[1]
    assert type_ == u"resource"


def test_request_signals(app):
    start_receiver = mock.Mock()
    finish_receiver = mock.Mock()
    with signals.request_started.connected_to(start_receiver):
        with signals.request_finished.connected_to(finish_receiver):
            app.get(u"/")
    assert start_receiver.call_count == 1
    assert finish_receiver.call_count == 1

    with signals.request_started.connected_to(start_receiver):
        with signals.request_finished.connected_to(finish_receiver):
            app.get(u"/about")
    assert start_receiver.call_count == 2
    assert finish_receiver.call_count == 2


@pytest.mark.usefixtures(u"non_clean_db", u"with_request_context")
class TestUserSignals:
    def test_user_created(self):
        created = mock.Mock()
        with signals.user_created.connected_to(created):
            factories.User()
            assert created.call_count == 1

    def test_password_reset(self, app, monkeypatch):
        user = factories.User()
        request_reset = mock.Mock()
        monkeypatch.setattr(
            mailer, u"send_reset_link", mailer.create_reset_key
        )
        with signals.request_password_reset.connected_to(request_reset):
            app.post(
                url_for(u"user.request_reset"), data={u"user": user[u"name"]}
            )
            assert request_reset.call_count == 1

        perform_reset = mock.Mock()
        user_obj = model.User.get(user['id'])
        with signals.perform_password_reset.connected_to(perform_reset):
            app.post(
                url_for(
                    u"user.perform_reset",
                    id=user[u"id"],
                    key=user_obj.reset_key
                ),
                data={
                    u'password1': u'password123',
                    u'password2': u'password123',
                }
            )
            assert perform_reset.call_count == 1

    def test_login(self, app):
        user = factories.User(email='user@ckan.org', password=u"correct123")
        url = url_for(u"user.login")
        success = mock.Mock()
        fail = mock.Mock()
        invalid = factories.User.stub().name
        with signals_user_logged_in.connected_to(success):
            with signals.failed_login.connected_to(fail):
                data = {u"login": invalid, u"password": u"invalid"}
                app.post(url, data=data)
                assert success.call_count == 0
                assert fail.call_count == 1

                data = {u"login": user[u"name"], u"password": u"invalid"}
                app.post(url, data=data)
                assert success.call_count == 0
                assert fail.call_count == 2

                data = {u"login": invalid, u"password": u"correct123"}
                app.post(url, data=data)
                assert success.call_count == 0
                assert fail.call_count == 3

                data = {u"login": user[u"name"], u"password": u"correct123"}
                app.post(url, data=data)
                assert success.call_count == 1
                assert fail.call_count == 3
