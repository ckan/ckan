"""
"""
from pylons import config
from ckan.lib.mailer import _mail_recipient
from ckan.tests import *

from smtpd import SMTPServer

class TestMailer(TestController):

    def setup(self):
        config['smtp_server'] = 'localhost:667511'
        config['ckan.mail_from'] = 'info@ckan.net'
        class TestSMTPServer(SMTPServer):
            def process_message(zelf, peer, mailfrom, rcpttos, data):
                print "FOO"
                return self.process_message(peer, mailfrom, rcpttos, data)
        self.server = TestSMTPServer(('localhost', 6675), None)

    def test_mail_recipient(self):
    #    def tests(s, peer, mailfrom, rcpttos, data):
    #        assert 'info@ckan.net' in mailfrom
    #        assert 'foo@bar.com' in recpttos
    #        assert 'i am a banana' in data
    #    #self.process_message = tests
    #    _mail_recipient('fooman', 'foo@localhost', 
    #            'banaman', 'http://banana.com',
    #            'i am a banana', 'this is a test')
        pass
