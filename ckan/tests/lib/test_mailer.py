from nose.tools import assert_equal, assert_raises, assert_in
from pylons import config
from email.mime.text import MIMEText
import hashlib

import ckan.model as model
import ckan.lib.mailer as mailer
from ckan.tests.legacy.mock_mail_server import SmtpServerHarness

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories


class TestMailer(SmtpServerHarness):

    @classmethod
    def setup_class(cls):

        helpers.reset_db()

        smtp_server = config.get('smtp.test_server')
        if smtp_server:
            host, port = smtp_server.split(':')
            port = (int(port) +
                    int(str(hashlib.md5(cls.__name__).hexdigest())[0], 16))
            config['smtp.test_server'] = '%s:%s' % (host, port)

        # Created directly to avoid email validation
        user_without_email = model.User(name='mary', email=None)
        model.Session.add(user_without_email)
        model.Session.commit()
        SmtpServerHarness.setup_class()

    @classmethod
    def teardown_class(cls):
        SmtpServerHarness.teardown_class()
        helpers.reset_db()

    def setup(self):
        self.clear_smtp_messages()

    def mime_encode(self, msg, recipient_name):
        text = MIMEText(msg.encode('utf-8'), 'plain', 'utf-8')
        encoded_body = text.get_payload().strip()
        return encoded_body

    def test_mail_recipient(self):
        user = factories.User()

        msgs = self.get_smtp_messages()
        assert_equal(msgs, [])

        # send email
        test_email = {'recipient_name': 'Bob',
                      'recipient_email': user['email'],
                      'subject': 'Meeting',
                      'body': 'The meeting is cancelled.',
                      'headers': {'header1': 'value1'}}
        mailer.mail_recipient(**test_email)

        # check it went to the mock smtp server
        msgs = self.get_smtp_messages()
        assert_equal(len(msgs), 1)
        msg = msgs[0]
        assert_equal(msg[1], config['smtp.mail_from'])
        assert_equal(msg[2], [test_email['recipient_email']])
        assert test_email['headers'].keys()[0] in msg[3], msg[3]
        assert test_email['headers'].values()[0] in msg[3], msg[3]
        assert test_email['subject'] in msg[3], msg[3]
        expected_body = self.mime_encode(test_email['body'],
                                         test_email['recipient_name'])
        assert_in(expected_body, msg[3])

    def test_mail_user(self):

        user = factories.User()
        user_obj = model.User.by_name(user['name'])

        msgs = self.get_smtp_messages()
        assert_equal(msgs, [])

        # send email
        test_email = {'recipient': user_obj,
                      'subject': 'Meeting',
                      'body': 'The meeting is cancelled.',
                      'headers': {'header1': 'value1'}}
        mailer.mail_user(**test_email)

        # check it went to the mock smtp server
        msgs = self.get_smtp_messages()
        assert_equal(len(msgs), 1)
        msg = msgs[0]
        assert_equal(msg[1], config['smtp.mail_from'])
        assert_equal(msg[2], [user['email']])
        assert test_email['headers'].keys()[0] in msg[3], msg[3]
        assert test_email['headers'].values()[0] in msg[3], msg[3]
        assert test_email['subject'] in msg[3], msg[3]
        expected_body = self.mime_encode(test_email['body'],
                                         user['name'])

        assert_in(expected_body, msg[3])

    def test_mail_user_without_email(self):
        # send email
        test_email = {'recipient': model.User.by_name(u'mary'),
                      'subject': 'Meeting',
                      'body': 'The meeting is cancelled.',
                      'headers': {'header1': 'value1'}}
        assert_raises(mailer.MailerException, mailer.mail_user, **test_email)

    def test_send_reset_email(self):
        user = factories.User()
        user_obj = model.User.by_name(user['name'])

        mailer.send_reset_link(user_obj)

        # check it went to the mock smtp server
        msgs = self.get_smtp_messages()
        assert_equal(len(msgs), 1)
        msg = msgs[0]
        assert_equal(msg[1], config['smtp.mail_from'])
        assert_equal(msg[2], [user['email']])
        assert 'Reset' in msg[3], msg[3]
        test_msg = mailer.get_reset_link_body(user_obj)
        expected_body = self.mime_encode(test_msg,
                                         user['name'])

        assert_in(expected_body, msg[3])

    def test_send_invite_email(self):
        user = factories.User()
        user_obj = model.User.by_name(user['name'])
        assert user_obj.reset_key is None, user_obj

        # send email
        mailer.send_invite(user_obj)

        # check it went to the mock smtp server
        msgs = self.get_smtp_messages()
        assert_equal(len(msgs), 1)
        msg = msgs[0]
        assert_equal(msg[1], config['smtp.mail_from'])
        assert_equal(msg[2], [user['email']])
        test_msg = mailer.get_invite_body(user_obj)
        expected_body = self.mime_encode(test_msg,
                                         user['name'])

        assert_in(expected_body, msg[3])
        assert user_obj.reset_key is not None, user

    @helpers.change_config('ckan.emails.reset_password.subject', 'Password!')
    def test_send_reset_email_custom_subject(self):
        user = factories.User()
        user_obj = model.User.by_name(user['name'])

        mailer.send_reset_link(user_obj)

        # check it went to the mock smtp server
        msgs = self.get_smtp_messages()
        assert_equal(len(msgs), 1)
        msg = msgs[0]

        assert_in('Password!', msg[3])

    @helpers.change_config('ckan.emails.invite_user.subject', 'Invite!')
    def test_send_invite_custom_subject(self):
        user = factories.User()
        user_obj = model.User.by_name(user['name'])

        mailer.send_invite(user_obj)

        # check it went to the mock smtp server
        msgs = self.get_smtp_messages()
        assert_equal(len(msgs), 1)
        msg = msgs[0]

        assert_in('Invite!', msg[3])
