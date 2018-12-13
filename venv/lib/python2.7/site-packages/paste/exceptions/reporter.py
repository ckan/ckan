# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
import smtplib
import time
try:
    from socket import sslerror
except ImportError:
    sslerror = None
from paste.exceptions import formatter

class Reporter(object):

    def __init__(self, **conf):
        for name, value in conf.items():
            if not hasattr(self, name):
                raise TypeError(
                    "The keyword argument %s was not expected"
                    % name)
            setattr(self, name, value)
        self.check_params()

    def check_params(self):
        pass

    def format_date(self, exc_data):
        return time.strftime('%c', exc_data.date)

    def format_html(self, exc_data, **kw):
        return formatter.format_html(exc_data, **kw)

    def format_text(self, exc_data, **kw):
        return formatter.format_text(exc_data, **kw)

class EmailReporter(Reporter):

    to_addresses = None
    from_address = None
    smtp_server = 'localhost'
    smtp_username = None
    smtp_password = None
    smtp_use_tls = False
    subject_prefix = ''

    def report(self, exc_data):
        msg = self.assemble_email(exc_data)
        server = smtplib.SMTP(self.smtp_server)
        if self.smtp_use_tls:
            server.ehlo()
            server.starttls()
            server.ehlo()
        if self.smtp_username and self.smtp_password:
            server.login(self.smtp_username, self.smtp_password)
        server.sendmail(self.from_address,
                        self.to_addresses, msg.as_string())
        try:
            server.quit()
        except sslerror:
            # sslerror is raised in tls connections on closing sometimes
            pass

    def check_params(self):
        if not self.to_addresses:
            raise ValueError("You must set to_addresses")
        if not self.from_address:
            raise ValueError("You must set from_address")
        if isinstance(self.to_addresses, (str, unicode)):
            self.to_addresses = [self.to_addresses]

    def assemble_email(self, exc_data):
        short_html_version = self.format_html(
            exc_data, show_hidden_frames=False)
        long_html_version = self.format_html(
            exc_data, show_hidden_frames=True)
        text_version = self.format_text(
            exc_data, show_hidden_frames=False)
        msg = MIMEMultipart()
        msg.set_type('multipart/alternative')
        msg.preamble = msg.epilogue = ''
        text_msg = MIMEText(text_version)
        text_msg.set_type('text/plain')
        text_msg.set_param('charset', 'ASCII')
        msg.attach(text_msg)
        html_msg = MIMEText(short_html_version)
        html_msg.set_type('text/html')
        # @@: Correct character set?
        html_msg.set_param('charset', 'UTF-8')
        html_long = MIMEText(long_html_version)
        html_long.set_type('text/html')
        html_long.set_param('charset', 'UTF-8')
        msg.attach(html_msg)
        msg.attach(html_long)
        subject = '%s: %s' % (exc_data.exception_type,
                              formatter.truncate(str(exc_data.exception_value)))
        msg['Subject'] = self.subject_prefix + subject
        msg['From'] = self.from_address
        msg['To'] = ', '.join(self.to_addresses)
        return msg

class LogReporter(Reporter):

    filename = None
    show_hidden_frames = True

    def check_params(self):
        assert self.filename is not None, (
            "You must give a filename")

    def report(self, exc_data):
        text = self.format_text(
            exc_data, show_hidden_frames=self.show_hidden_frames)
        f = open(self.filename, 'a')
        try:
            f.write(text + '\n' + '-'*60 + '\n')
        finally:
            f.close()

class FileReporter(Reporter):

    file = None
    show_hidden_frames = True

    def check_params(self):
        assert self.file is not None, (
            "You must give a file object")

    def report(self, exc_data):
        text = self.format_text(
            exc_data, show_hidden_frames=self.show_hidden_frames)
        self.file.write(text + '\n' + '-'*60 + '\n')

class WSGIAppReporter(Reporter):

    def __init__(self, exc_data):
        self.exc_data = exc_data

    def __call__(self, environ, start_response):
        start_response('500 Server Error', [('Content-type', 'text/html')])
        return [formatter.format_html(self.exc_data)]
