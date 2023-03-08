# encoding: utf-8

import os
import pytest


import ckan.model as model
import ckan.lib.mailer as mailer
from ckan.tests import factories
from ckan.lib.base import render
from ckan.common import config

from ckan.tests.lib.test_mailer import MailerBase


@pytest.mark.usefixtures("with_request_context", "clean_db", "with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "example_theme_custom_emails")
class TestExampleCustomEmailsPlugin(MailerBase):

    def _get_template_content(self, name):

        templates_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "templates", "emails"
        )
        with open(os.path.join(templates_path, name), "r") as f:
            return f.read()

    def test_reset_password_custom_subject(self, mail_server):
        user = factories.User()
        user_obj = model.User.by_name(user["name"])

        mailer.send_reset_link(user_obj)

        # check it went to the mock smtp server
        msgs = mail_server.get_smtp_messages()
        assert len(msgs) == 1
        msg = msgs[0]
        extra_vars = {"site_title": config.get("ckan.site_title")}
        expected = render(
            "emails/reset_password_subject.txt", extra_vars
        )
        expected = expected.split("\n")[0]

        subject = self.get_email_subject(msg[3])
        assert expected == subject
        assert "**test**" in subject

    def test_reset_password_custom_body(self, mail_server):
        user = factories.User()
        user_obj = model.User.by_name(user["name"])

        mailer.send_reset_link(user_obj)

        # check it went to the mock smtp server
        msgs = mail_server.get_smtp_messages()
        assert len(msgs) == 1
        msg = msgs[0]
        extra_vars = {"reset_link": mailer.get_reset_link(user_obj)}
        expected = render("emails/reset_password.txt", extra_vars)
        body = self.get_email_body(msg[3]).decode()
        assert expected == body.strip()
        assert "**test**" in body

    def test_invite_user_custom_subject(self, mail_server):
        user = factories.User()
        user_obj = model.User.by_name(user["name"])

        mailer.send_invite(user_obj)

        # check it went to the mock smtp server
        msgs = mail_server.get_smtp_messages()
        assert len(msgs) == 1
        msg = msgs[0]
        extra_vars = {
            "site_title": config.get("ckan.site_title"),
        }
        expected = render("emails/invite_user_subject.txt", extra_vars)
        expected = expected.split("\n")[0]

        subject = self.get_email_subject(msg[3])
        assert expected == subject
        assert "**test**" in subject

    def test_invite_user_custom_body(self, mail_server):
        user = factories.User()
        user_obj = model.User.by_name(user["name"])

        mailer.send_invite(user_obj)

        # check it went to the mock smtp server
        msgs = mail_server.get_smtp_messages()
        assert len(msgs) == 1
        msg = msgs[0]
        extra_vars = {
            "reset_link": mailer.get_reset_link(user_obj),
            "user_name": user["name"],
            "site_title": config.get("ckan.site_title"),
        }
        expected = render("emails/invite_user.txt", extra_vars)
        body = self.get_email_body(msg[3]).decode()
        assert expected == body.strip()
        assert "**test**" in body
