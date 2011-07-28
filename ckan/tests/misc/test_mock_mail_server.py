import time
from nose.tools import assert_equal
from pylons import config
from email.mime.text import MIMEText

from ckan.tests.pylons_controller import PylonsTestCase
from ckan.tests.mock_mail_server import SmtpServerHarness
from ckan.lib.mailer import mail_recipient

class TestMockMailServer(SmtpServerHarness, PylonsTestCase):
    @classmethod
    def setup_class(cls):
        SmtpServerHarness.setup_class()
        PylonsTestCase.setup_class()

    @classmethod
    def teardown_class(cls):
        SmtpServerHarness.teardown_class()

    def test_basic(self):
        msgs = self.get_smtp_messages()
        assert_equal(msgs, [])

        test_email = {'recipient_name': 'Bob',
                      'recipient_email':'bob@bob.net',
                      'subject': 'Meeting', 
                      'body': 'The meeting is cancelled.',
                      'headers': {'header1': 'value1'}}
        mail_recipient(**test_email)
        time.sleep(0.1)

        msgs = self.get_smtp_messages()
        assert_equal(len(msgs), 1)
