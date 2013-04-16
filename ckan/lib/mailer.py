import smtplib
import logging
import uuid
from time import time
from email.mime.text import MIMEText
from email.header import Header
from email import Utils
from urlparse import urljoin

from pylons import config
import paste.deploy.converters

import ckan
import ckan.model as model
import ckan.lib.helpers as h

from ckan.common import _, g

log = logging.getLogger(__name__)

class MailerException(Exception):
    pass

def add_msg_niceties(recipient_name, body, sender_name, sender_url):
    return _(u"Dear %s,") % recipient_name \
           + u"\r\n\r\n%s\r\n\r\n" % body \
           + u"--\r\n%s (%s)" % (sender_name, sender_url)

def _mail_recipient(recipient_name, recipient_email,
        sender_name, sender_url, subject,
        body, headers={}):
    mail_from = config.get('smtp.mail_from')
    body = add_msg_niceties(recipient_name, body, sender_name, sender_url)
    msg = MIMEText(body.encode('utf-8'), 'plain', 'utf-8')
    for k, v in headers.items(): msg[k] = v
    subject = Header(subject.encode('utf-8'), 'utf-8')
    msg['Subject'] = subject
    msg['From'] = _("%s <%s>") % (sender_name, mail_from)
    recipient = u"%s <%s>" % (recipient_name, recipient_email)
    msg['To'] = Header(recipient, 'utf-8')
    msg['Date'] = Utils.formatdate(time())
    msg['X-Mailer'] = "CKAN %s" % ckan.__version__

    # Send the email using Python's smtplib.
    smtp_connection = smtplib.SMTP()
    if 'smtp.test_server' in config:
        # If 'smtp.test_server' is configured we assume we're running tests,
        # and don't use the smtp.server, starttls, user, password etc. options.
        smtp_server = config['smtp.test_server']
        smtp_starttls = False
        smtp_user = None
        smtp_password = None
    else:
        smtp_server = config.get('smtp.server', 'localhost')
        smtp_starttls = paste.deploy.converters.asbool(
                config.get('smtp.starttls'))
        smtp_user = config.get('smtp.user')
        smtp_password = config.get('smtp.password')
    smtp_connection.connect(smtp_server)
    try:
        #smtp_connection.set_debuglevel(True)

        # Identify ourselves and prompt the server for supported features.
        smtp_connection.ehlo()

        # If 'smtp.starttls' is on in CKAN config, try to put the SMTP
        # connection into TLS mode.
        if smtp_starttls:
            if smtp_connection.has_extn('STARTTLS'):
                smtp_connection.starttls()
                # Re-identify ourselves over TLS connection.
                smtp_connection.ehlo()
            else:
                raise MailerException("SMTP server does not support STARTTLS")

        # If 'smtp.user' is in CKAN config, try to login to SMTP server.
        if smtp_user:
            assert smtp_password, ("If smtp.user is configured then "
                    "smtp.password must be configured as well.")
            smtp_connection.login(smtp_user, smtp_password)

        smtp_connection.sendmail(mail_from, [recipient_email], msg.as_string())
        log.info("Sent email to {0}".format(recipient_email))

    except smtplib.SMTPException, e:
        msg = '%r' % e
        log.exception(msg)
        raise MailerException(msg)
    finally:
        smtp_connection.quit()

def mail_recipient(recipient_name, recipient_email, subject,
        body, headers={}):
    return _mail_recipient(recipient_name, recipient_email,
            g.site_title, g.site_url, subject, body, headers=headers)

def mail_user(recipient, subject, body, headers={}):
    if (recipient.email is None) or not len(recipient.email):
        raise MailerException(_("No recipient email address available!"))
    mail_recipient(recipient.display_name, recipient.email, subject,
            body, headers=headers)


RESET_LINK_MESSAGE = _(
'''You have requested your password on %(site_title)s to be reset.

Please click the following link to confirm this request:

   %(reset_link)s
''')

def make_key():
    return uuid.uuid4().hex[:10]

def create_reset_key(user):
    user.reset_key = unicode(make_key())
    model.repo.commit_and_remove()

def get_reset_link(user):
    return urljoin(g.site_url,
                   h.url_for(controller='user',
                           action='perform_reset',
                           id=user.id,
                           key=user.reset_key))

def get_reset_link_body(user):
    d = {
        'reset_link': get_reset_link(user),
        'site_title': g.site_title
        }
    return RESET_LINK_MESSAGE % d

def send_reset_link(user):
    create_reset_key(user)
    body = get_reset_link_body(user)
    mail_user(user, _('Reset your password'), body)

def verify_reset_link(user, key):
    if not key:
        return False
    if not user.reset_key or len(user.reset_key) < 5:
        return False
    return key.strip() == user.reset_key



