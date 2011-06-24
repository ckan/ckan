from datetime import datetime, timedelta
import smtplib
import logging
from time import time

from email.mime.text import MIMEText
from email.header import Header
from email import Utils

from pylons.i18n.translation import _
from pylons import config, g
from ckan import __version__

log = logging.getLogger(__name__)

class MailerException(Exception):
    pass

def _mail_recipient(recipient_name, recipient_email,
        sender_name, sender_url, subject,
        body, headers={}):
    mail_from = config.get('ckan.mail_from')
    body = _(u"Dear %s,") % recipient_name \
         + u"\r\n\r\n%s\r\n\r\n" % body \
         + u"--\r\n%s (%s)" % (sender_name, sender_url)
    msg = MIMEText(body.encode('utf-8'), 'plain', 'utf-8')
    for k, v in headers.items(): msg[k] = v
    subject = Header(subject.encode('utf-8'), 'utf-8')
    msg['Subject'] = subject
    msg['From'] = _("%s <%s>") % (sender_url, mail_from)
    recipient = u"%s <%s>" % (recipient_name, recipient_email)
    msg['To'] = Header(recipient, 'utf-8')
    msg['Date'] = Utils.formatdate(time())
    msg['X-Mailer'] = "CKAN %s" % __version__
    try:
        server = smtplib.SMTP(config.get('smtp_server', 'localhost'))
        server.set_debuglevel(1)
        server.sendmail(mail_from, [recipient_email], msg.as_string())
        server.quit()
    except Exception, e:
        log.exception(e)
        raise MailerException(e.message)

def mail_recipient(recipient_name, recipient_email, subject, 
        body, headers={}):
    return _mail_recipient(recipient_name, recipient_email,
            g.site_title, g.site_url, subject, body, headers=headers)

def mail_user(recipient, subject, body, headers={}):
    if (recipient.email is None) and len(recipient.email):
        raise MailerException(_("No recipient email address available!"))
    mail_recipient(recipient.display_name, recipient.email, subject, 
            body, headers=headers)


