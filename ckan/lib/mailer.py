import smtplib
import logging
import uuid
from time import time
from email.mime.text import MIMEText
from email.header import Header
from email import Utils
from urlparse import urljoin

from pylons.i18n.translation import _
from pylons import config, g
from ckan import model, __version__
from ckan.lib.helpers import url_for

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
    mail_from = config.get('ckan.mail_from')
    body = add_msg_niceties(recipient_name, body, sender_name, sender_url)
    msg = MIMEText(body.encode('utf-8'), 'plain', 'utf-8')
    for k, v in headers.items(): msg[k] = v
    subject = Header(subject.encode('utf-8'), 'utf-8')
    msg['Subject'] = subject
    msg['From'] = _("%s <%s>") % (sender_name, mail_from)
    recipient = u"%s <%s>" % (recipient_name, recipient_email)
    msg['To'] = Header(recipient, 'utf-8')
    msg['Date'] = Utils.formatdate(time())
    msg['X-Mailer'] = "CKAN %s" % __version__
    try:
        server = smtplib.SMTP(
            config.get('test_smtp_server',
                       config.get('smtp_server', 'localhost')))
        #server.set_debuglevel(1)
        server.sendmail(mail_from, [recipient_email], msg.as_string())
        server.quit()
    except Exception, e:
        msg = '%r' % e
        log.exception(msg)
        raise MailerException(msg)

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
                   url_for(controller='user',
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
    if not user.reset_key or len(user.reset_key) < 5:
        return False
    return key.strip() == user.reset_key



