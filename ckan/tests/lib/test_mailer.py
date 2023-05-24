# encoding: utf-8

import base64
import pytest
import six
import io
from email.header import decode_header
from email.mime.text import MIMEText
from email.parser import Parser
import email.utils

import ckan.lib.helpers as h
import ckan.lib.mailer as mailer
import ckan.model as model
import ckan.tests.factories as factories
from ckan.common import config


class MailerBase(object):
    def mime_encode(self, msg, recipient_name, subtype='plain'):
        text = MIMEText(msg.encode("utf-8"), subtype, "utf-8")
        encoded_body = text.get_payload().strip()
        return encoded_body

    def get_email_body(self, msg):
        payload = Parser().parsestr(msg).get_payload()
        return base64.b64decode(payload)

    def get_email_subject(self, msg):
        header = Parser().parsestr(msg)["Subject"]
        return decode_header(header)[0][0]


@pytest.mark.usefixtures("with_request_context", "non_clean_db")
class TestMailer(MailerBase):
    def test_mail_recipient(self, mail_server):
        user = factories.User()

        msgs = mail_server.get_smtp_messages()
        assert msgs == []

        # send email
        test_email = {
            "recipient_name": "Bob",
            "recipient_email": user["email"],
            "subject": "Meeting",
            "body": "The meeting is cancelled.\n",
            "headers": {"header1": "value1"},
        }
        mailer.mail_recipient(**test_email)

        # check it went to the mock smtp server
        msgs = mail_server.get_smtp_messages()
        assert len(msgs) == 1
        msg = msgs[0]
        assert msg[1] == config["smtp.mail_from"]
        assert msg[2] == [test_email["recipient_email"]]
        assert list(test_email["headers"].keys())[0] in msg[3], msg[3]
        assert list(test_email["headers"].values())[0] in msg[3], msg[3]
        assert test_email["subject"] in msg[3], msg[3]
        assert "X-Mailer" in msg[3], "Missing X-Mailer header"
        expected_body = self.mime_encode(
            test_email["body"], test_email["recipient_name"]
        )
        assert expected_body in msg[3]

    @pytest.mark.ckan_config('ckan.hide_version', True)
    def test_mail_recipient_hiding_mailer(self, mail_server):
        user = factories.User()

        msgs = mail_server.get_smtp_messages()
        assert msgs == []

        # send email
        test_email = {
            "recipient_name": "Bob",
            "recipient_email": user["email"],
            "subject": "Meeting",
            "body": "The meeting is cancelled.\n",
            "headers": {"header1": "value1"},
        }
        mailer.mail_recipient(**test_email)

        # check it went to the mock smtp server
        msgs = mail_server.get_smtp_messages()
        assert len(msgs) == 1
        msg = msgs[0]
        assert msg[1] == config["smtp.mail_from"]
        assert msg[2] == [test_email["recipient_email"]]
        assert list(test_email["headers"].keys())[0] in msg[3], msg[3]
        assert list(test_email["headers"].values())[0] in msg[3], msg[3]
        assert test_email["subject"] in msg[3], msg[3]
        assert msg[3].startswith('Content-Type: text/plain'), msg[3]
        assert "X-Mailer" not in msg[3], \
            "Should have skipped X-Mailer header"
        expected_body = self.mime_encode(
            test_email["body"], test_email["recipient_name"]
        )
        assert expected_body in msg[3]

    def test_mail_recipient_with_html(self, mail_server):
        user = factories.User()

        msgs = mail_server.get_smtp_messages()
        assert msgs == []

        # send email
        test_email = {
            "recipient_name": "Bob",
            "recipient_email": user["email"],
            "subject": "Meeting",
            "body": "The meeting is cancelled.\n",
            "body_html": "The <a href=\"meeting\">meeting</a> is cancelled.\n",
            "headers": {"header1": "value1"},
        }
        mailer.mail_recipient(**test_email)

        # check it went to the mock smtp server
        msgs = mail_server.get_smtp_messages()
        assert len(msgs) == 1
        msg = msgs[0]
        assert msg[1] == config["smtp.mail_from"]
        assert msg[2] == [test_email["recipient_email"]]
        assert list(test_email["headers"].keys())[0] in msg[3], msg[3]
        assert list(test_email["headers"].values())[0] in msg[3], msg[3]
        assert test_email["subject"] in msg[3], msg[3]
        assert 'Content-Type: multipart' in msg[3]
        expected_plain_body = self.mime_encode(
            test_email["body"], test_email["recipient_name"],
            subtype='plain'
        )
        assert expected_plain_body in msg[3]
        expected_html_body = self.mime_encode(
            test_email["body_html"], test_email["recipient_name"],
            subtype='html'
        )
        assert expected_html_body in msg[3]

    def test_mail_user(self, mail_server):

        user = factories.User()
        user_obj = model.User.by_name(user["name"])

        msgs = mail_server.get_smtp_messages()
        assert msgs == []

        # send email
        test_email = {
            "recipient": user_obj,
            "subject": "Meeting",
            "body": "The meeting is cancelled.\n",
            "headers": {"header1": "value1"},
        }
        mailer.mail_user(**test_email)

        # check it went to the mock smtp server
        msgs = mail_server.get_smtp_messages()
        assert len(msgs) == 1
        msg = msgs[0]
        assert msg[1] == config["smtp.mail_from"]
        assert msg[2] == [user["email"]]
        assert list(test_email["headers"].keys())[0] in msg[3], msg[3]
        assert list(test_email["headers"].values())[0] in msg[3], msg[3]
        assert test_email["subject"] in msg[3], msg[3]
        expected_body = self.mime_encode(test_email["body"], user["name"])

        assert expected_body in msg[3]

    def test_mail_user_without_email(self):
        # send email
        mary = model.User(email=None)
        # model.Session.add(mary)
        # model.Session.commit()

        test_email = {
            "recipient": mary,
            "subject": "Meeting",
            "body": "The meeting is cancelled.",
            "headers": {"header1": "value1"},
        }
        with pytest.raises(mailer.MailerException):
            mailer.mail_user(**test_email)

    @pytest.mark.ckan_config("ckan.site_title", "My CKAN instance")
    def test_from_field_format(self, mail_server):

        msgs = mail_server.get_smtp_messages()
        assert msgs == []

        # send email
        test_email = {
            "recipient_name": "Bob",
            "recipient_email": "Bob@bob.com",
            "subject": "Meeting",
            "body": "The meeting is cancelled.",
            "headers": {"header1": "value1"},
        }
        mailer.mail_recipient(**test_email)

        # check it went to the mock smtp server
        msgs = mail_server.get_smtp_messages()
        msg = msgs[0]

        expected_from_header = email.utils.formataddr((
            config.get("ckan.site_title"),
            config.get("smtp.mail_from")
        ))

        assert expected_from_header in msg[3]

    def test_send_reset_email(self, mail_server):
        user = factories.User()
        user_obj = model.User.by_name(user["name"])

        mailer.send_reset_link(user_obj)

        # check it went to the mock smtp server
        msgs = mail_server.get_smtp_messages()
        assert len(msgs) == 1
        msg = msgs[0]
        assert msg[1] == config["smtp.mail_from"]
        assert msg[2] == [user["email"]]
        assert "Reset" in msg[3], msg[3]
        test_msg = mailer.get_reset_link_body(user_obj)
        expected_body = self.mime_encode(test_msg + '\n', user["name"])

        assert expected_body in msg[3]

    def test_send_invite_email(self, mail_server):
        user = factories.User()
        user_obj = model.User.by_name(user["name"])
        assert user_obj.reset_key is None, user_obj

        # send email
        mailer.send_invite(user_obj)

        # check it went to the mock smtp server
        msgs = mail_server.get_smtp_messages()
        assert len(msgs) == 1
        msg = msgs[0]
        assert msg[1] == config["smtp.mail_from"]
        assert msg[2] == [user["email"]]
        test_msg = mailer.get_invite_body(user_obj)
        expected_body = self.mime_encode(test_msg + '\n', user["name"])

        assert expected_body in msg[3]
        assert user_obj.reset_key is not None, user

    def test_send_invite_email_with_group(self, mail_server):
        user = factories.User()
        user_obj = model.User.by_name(user["name"])

        group = factories.Group()
        role = "member"

        # send email
        mailer.send_invite(user_obj, group_dict=group, role=role)

        # check it went to the mock smtp server
        msgs = mail_server.get_smtp_messages()
        msg = msgs[0]
        body = self.get_email_body(msg[3])
        assert group["title"] in six.ensure_text(body)
        assert h.roles_translated()[role] in six.ensure_text(body)

    def test_send_invite_email_with_org(self, mail_server):
        user = factories.User()
        user_obj = model.User.by_name(user["name"])

        org = factories.Organization()
        role = "admin"

        # send email
        mailer.send_invite(user_obj, group_dict=org, role=role)

        # check it went to the mock smtp server
        msgs = mail_server.get_smtp_messages()
        msg = msgs[0]
        body = self.get_email_body(msg[3])
        assert org["title"] in six.ensure_text(body)
        assert h.roles_translated()[role] in six.ensure_text(body)

    @pytest.mark.ckan_config("smtp.server", "999.999.999.999")
    def test_bad_smtp_host(self):
        test_email = {
            "recipient_name": "Bob",
            "recipient_email": "b@example.com",
            "subject": "Meeting",
            "body": "The meeting is cancelled.",
            "headers": {"header1": "value1"},
        }
        with pytest.raises(mailer.MailerException):
            mailer.mail_recipient(**test_email)

    @pytest.mark.ckan_config("smtp.reply_to", "norply@ckan.org")
    def test_reply_to(self, mail_server):

        msgs = mail_server.get_smtp_messages()
        assert msgs == []

        # send email
        test_email = {
            "recipient_name": "Bob",
            "recipient_email": "Bob@bob.com",
            "subject": "Meeting",
            "body": "The meeting is cancelled.",
            "headers": {"header1": "value1"},
        }
        mailer.mail_recipient(**test_email)

        # check it went to the mock smtp server
        msgs = mail_server.get_smtp_messages()
        msg = msgs[0]

        expected_from_header = "Reply-to: {}".format(
            config.get("smtp.reply_to")
        )

        assert expected_from_header in msg[3]

    @pytest.mark.ckan_config("smtp.reply_to", "norply@ckan.org")
    def test_reply_to_ext_headers_overwrite(self, mail_server):

        msgs = mail_server.get_smtp_messages()
        assert msgs == []

        # send email
        test_email = {
            "recipient_name": "Bob",
            "recipient_email": "Bob@bob.com",
            "subject": "Meeting",
            "body": "The meeting is cancelled.",
            "headers": {"Reply-to": "norply@ckanext.org"},
        }
        mailer.mail_recipient(**test_email)

        # check it went to the mock smtp server
        msgs = mail_server.get_smtp_messages()
        msg = msgs[0]

        expected_from_header = 'Reply-to: norply@ckanext.org'

        assert expected_from_header in msg[3]

    def test_mail_user_with_attachments(self, mail_server):

        user = factories.User()
        user_obj = model.User.by_name(user["name"])

        msgs = mail_server.get_smtp_messages()
        assert msgs == []

        # send email
        test_email = {
            "recipient": user_obj,
            "subject": "Meeting",
            "body": "The meeting is cancelled.\n",
            "headers": {"header1": "value1"},
            "attachments": [
                ("strategy.pdf", io.BytesIO(b'Some fake pdf'), 'application/pdf'),
                ("goals.png", io.BytesIO(b'Some fake png'), 'image/png'),
            ]
        }
        mailer.mail_user(**test_email)

        # check it went to the mock smtp server
        msgs = mail_server.get_smtp_messages()
        assert len(msgs) == 1
        msg = msgs[0]
        assert msg[1] == config["smtp.mail_from"]
        assert msg[2] == [user["email"]]
        assert list(test_email["headers"].keys())[0] in msg[3], msg[3]
        assert list(test_email["headers"].values())[0] in msg[3], msg[3]
        assert test_email["subject"] in msg[3], msg[3]

        for item in [
            "strategy.pdf", base64.b64encode(b'Some fake pdf').decode(), "application/pdf",
            "goals.png", base64.b64encode(b'Some fake png').decode(), "image/png",
        ]:
            assert item in msg[3]

    def test_mail_user_with_attachments_no_media_type_provided(self, mail_server):

        user = factories.User()
        user_obj = model.User.by_name(user["name"])

        msgs = mail_server.get_smtp_messages()
        assert msgs == []

        # send email
        test_email = {
            "recipient": user_obj,
            "subject": "Meeting",
            "body": "The meeting is cancelled.\n",
            "headers": {"header1": "value1"},
            "attachments": [
                ("strategy.pdf", io.BytesIO(b'Some fake pdf')),
                ("goals.png", io.BytesIO(b'Some fake png')),
            ]
        }
        mailer.mail_user(**test_email)

        # check it went to the mock smtp server
        msgs = mail_server.get_smtp_messages()
        assert len(msgs) == 1
        msg = msgs[0]

        for item in [
            "strategy.pdf", "application/pdf",
            "goals.png", "image/png",
        ]:
            assert item in msg[3]
