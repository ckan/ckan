from nose.tools import assert_equal, assert_raises
from pylons import config
from email.mime.text import MIMEText
import hashlib

import ckan.model as model
import ckan.lib.mailer as mailer
from ckan.tests.pylons_controller import PylonsTestCase
from ckan.tests.mock_mail_server import SmtpServerHarness
from ckan.lib.create_test_data import CreateTestData
from ckan.lib.base import g

class TestMailer(SmtpServerHarness, PylonsTestCase):
    @classmethod
    def setup_class(cls):
        smtp_server = config.get('smtp.test_server')
        if smtp_server:
            host, port = smtp_server.split(':')
            port = int(port) + int(str(hashlib.md5(cls.__name__).hexdigest())[0], 16)
            config['smtp.test_server'] = '%s:%s' % (host, port)
        CreateTestData.create_user(name='bob', email='bob@bob.net')
        CreateTestData.create_user(name='mary') #NB No email addr provided
        SmtpServerHarness.setup_class()
        PylonsTestCase.setup_class()

    @classmethod
    def teardown_class(cls):
        SmtpServerHarness.teardown_class()
        model.repo.rebuild_db()

    def setup(self):
        self.clear_smtp_messages()

    def mime_encode(self, msg, recipient_name):
        sender_name = g.site_title
        sender_url = g.site_url
        body = mailer.add_msg_niceties(recipient_name, msg, sender_name, sender_url)
        encoded_body = MIMEText(body.encode('utf-8'), 'plain', 'utf-8').get_payload().strip()
        return encoded_body

    def test_mail_recipient(self):
        msgs = self.get_smtp_messages()
        assert_equal(msgs, [])

        # send email
        test_email = {'recipient_name': 'Bob',
                      'recipient_email':'bob@bob.net',
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
        assert expected_body in msg[3], '%r not in %r' % (expected_body, msg[3])

    def test_mail_user(self):
        msgs = self.get_smtp_messages()
        assert_equal(msgs, [])

        # send email
        test_email = {'recipient': model.User.by_name(u'bob'),
                      'subject': 'Meeting', 
                      'body': 'The meeting is cancelled.',
                      'headers': {'header1': 'value1'}}
        mailer.mail_user(**test_email)

        # check it went to the mock smtp server
        msgs = self.get_smtp_messages()
        assert_equal(len(msgs), 1)
        msg = msgs[0]
        assert_equal(msg[1], config['smtp.mail_from'])
        assert_equal(msg[2], [model.User.by_name(u'bob').email])
        assert test_email['headers'].keys()[0] in msg[3], msg[3]
        assert test_email['headers'].values()[0] in msg[3], msg[3]
        assert test_email['subject'] in msg[3], msg[3]
        expected_body = self.mime_encode(test_email['body'],
                                         'bob')
        assert expected_body in msg[3], '%r not in %r' % (expected_body, msg[3])

    def test_mail_user_without_email(self):
        # send email
        test_email = {'recipient': model.User.by_name(u'mary'),
                      'subject': 'Meeting', 
                      'body': 'The meeting is cancelled.',
                      'headers': {'header1': 'value1'}}
        assert_raises(mailer.MailerException, mailer.mail_user, **test_email)

    def test_send_reset_email(self):
        # send email
        mailer.send_reset_link(model.User.by_name(u'bob'))

        # check it went to the mock smtp server
        msgs = self.get_smtp_messages()
        assert_equal(len(msgs), 1)
        msg = msgs[0]
        assert_equal(msg[1], config['smtp.mail_from'])
        assert_equal(msg[2], [model.User.by_name(u'bob').email])
        assert 'Reset' in msg[3], msg[3]
        test_msg = mailer.get_reset_link_body(model.User.by_name(u'bob'))
        expected_body = self.mime_encode(test_msg,
                                         u'bob')
        assert expected_body in msg[3], '%r not in %r' % (expected_body, msg[3])

        # reset link tested in user functional test

    def test_send_invite_email(self):
        user = model.User.by_name(u'bob')
        assert user.reset_key is None, user
        # send email
        mailer.send_invite(user)

        # check it went to the mock smtp server
        msgs = self.get_smtp_messages()
        assert_equal(len(msgs), 1)
        msg = msgs[0]
        assert_equal(msg[1], config['smtp.mail_from'])
        assert_equal(msg[2], [model.User.by_name(u'bob').email])
        test_msg = mailer.get_invite_body(model.User.by_name(u'bob'))
        expected_body = self.mime_encode(test_msg,
                                         u'bob') 
        assert expected_body in msg[3], '%r not in %r' % (expected_body, msg[3])
        assert user.reset_key is not None, user
        
        # reset link tested in user functional test
