# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
import smtplib
import ssl
import time
from weberror import formatter
from email.utils import formatdate

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
        ## FIXME: this should check the return value from this function:
        result = server.sendmail(self.from_address,
                        self.to_addresses, msg.as_string())
        try:
            server.quit()
        except ssl.SSLError:
            # SSLError is raised in tls connections on closing sometimes
            pass

    def check_params(self):
        if not self.to_addresses:
            raise ValueError("You must set to_addresses")
        if not self.from_address:
            raise ValueError("You must set from_address")
        if isinstance(self.to_addresses, (str, unicode)):
            self.to_addresses = [self.to_addresses]

    def assemble_email(self, exc_data):
        short_html_version, short_extra = self.format_html(
            exc_data, show_hidden_frames=False, show_extra_data=True)
        long_html_version, long_extra = self.format_html(
            exc_data, show_hidden_frames=True, show_extra_data=True)
        text_version = self.format_text(
            exc_data, show_hidden_frames=True, show_extra_data=True)[0]
        msg = MIMEMultipart()
        msg.set_type('multipart/alternative')
        msg.preamble = msg.epilogue = ''
        text_msg = MIMEText(as_str(text_version))
        text_msg.set_type('text/plain')
        text_msg.set_param('charset', 'UTF-8')
        msg.attach(text_msg)
        html_msg = MIMEText(as_str(short_html_version) + as_str(''.join(short_extra)))
        html_msg.set_type('text/html')
        html_msg.set_param('charset', 'UTF-8')
        html_long = MIMEText(as_str(long_html_version) + as_str(''.join(long_extra)))
        html_long.set_type('text/html')
        html_long.set_param('charset', 'UTF-8')
        msg.attach(html_msg)
        msg.attach(html_long)
        subject = as_str('%s: %s' % (exc_data.exception_type,
                                     formatter.truncate(str(exc_data.exception_value))))
        msg['Subject'] = as_str(self.subject_prefix) + subject
        msg['From'] = as_str(self.from_address)
        msg['To'] = as_str(', '.join(self.to_addresses))
        msg['Date'] = formatdate()
        return msg

class LogReporter(Reporter):

    filename = None
    show_hidden_frames = True

    def check_params(self):
        assert self.filename is not None, (
            "You must give a filename")

    def report(self, exc_data):
        text, head_text = self.format_text(
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
        text, head_text = self.format_text(
            exc_data, show_hidden_frames=self.show_hidden_frames)
        self.file.write(text + '\n' + '-'*60 + '\n')

class WSGIAppReporter(Reporter):

    def __init__(self, exc_data):
        self.exc_data = exc_data

    def __call__(self, environ, start_response):
        start_response('500 Server Error', [('Content-type', 'text/html')])
        return [formatter.format_html(self.exc_data)]

def as_str(v):
    if isinstance(v, str):
        return v
    if not isinstance(v, unicode):
        v = unicode(v)
    if isinstance(v, unicode):
        v = v.encode('utf8')
    return v
