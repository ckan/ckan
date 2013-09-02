import time
from nose.tools import assert_equal
from pylons import config
from email.mime.text import MIMEText
import hashlib

from ckan.tests.pylons_controller import PylonsTestCase
from ckan.tests.mock_mail_server import SmtpServerHarness
from ckan.lib.mailer import mail_recipient
from ckan.common import ckan_config

class TestMockMailServer(SmtpServerHarness, PylonsTestCase):
    @classmethod
    def setup_class(cls):
        smtp_server = config.get('smtp.test_server')
        if smtp_server:
            host, port = smtp_server.split(':')
            port = int(port) + int(str(hashlib.md5(cls.__name__).hexdigest())[0], 16)
            config['smtp.test_server'] = '%s:%s' % (host, port)
            ckan_config.store_for_tests()
            ckan_config.update_for_tests({'smtp_test_server': '%s:%s' % (host, port)})
        SmtpServerHarness.setup_class()
        PylonsTestCase.setup_class()

    @classmethod
    def teardown_class(cls):
        SmtpServerHarness.teardown_class()
        ckan_config.restore_for_tests()

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
