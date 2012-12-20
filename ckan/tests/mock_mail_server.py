import threading
import asyncore
import socket
from smtpd import SMTPServer
import hashlib

from pylons import config

from ckan.lib.mailer import _mail_recipient

class MockSmtpServer(SMTPServer):
    '''A mock SMTP server that operates in an asyncore loop'''
    def __init__(self, host, port):
        self.msgs = []
        SMTPServer.__init__(self, (host, port), None)
        
    def process_message(self, peer, mailfrom, rcpttos, data):
        self.msgs.append((peer, mailfrom, rcpttos, data))

    def get_smtp_messages(self):
        return self.msgs

    def clear_smtp_messages(self):
        self.msgs = []

class MockSmtpServerThread(threading.Thread):
    '''Runs the mock SMTP server in a thread'''
    def __init__(self, host, port):   
        self.assert_port_free(host, port)
        # init thread
        self._stop_event = threading.Event()
        self.thread_name = self.__class__
        threading.Thread.__init__(self, name=self.thread_name)
        # init smtp server
        self.server = MockSmtpServer(host, port)

    def assert_port_free(self, host, port):
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,
                               test_socket.getsockopt(socket.SOL_SOCKET,
                                                      socket.SO_REUSEADDR) | 1 )
        test_socket.bind((host, port))
        test_socket.close()
        
    def run(self):
        while not self._stop_event.isSet():
            asyncore.loop(timeout=0.01, count=1)

    def stop(self, timeout=None):
        self._stop_event.set()
        threading.Thread.join(self, timeout)
        self.server.close()

    def get_smtp_messages(self):
        return self.server.get_smtp_messages()

    def clear_smtp_messages(self):
        return self.server.clear_smtp_messages()
        
class SmtpServerHarness(object):
    '''Derive from this class to run MockSMTP - a test harness that
    records what email messages are requested to be sent by it.'''

    @classmethod
    def setup_class(cls):
        smtp_server  = config.get('smtp.test_server') or config['smtp_server']
        if ':' in smtp_server:
            host, port = smtp_server.split(':')
        else:
            host, port = smtp_server, 25
        cls.port = port
        cls.smtp_thread = MockSmtpServerThread(host, int(port))
        cls.smtp_thread.start()

    @classmethod
    def teardown_class(cls):
        cls.smtp_thread.stop()

    def get_smtp_messages(self):
        return self.smtp_thread.get_smtp_messages()

    def clear_smtp_messages(self):
        return self.smtp_thread.clear_smtp_messages()
    
