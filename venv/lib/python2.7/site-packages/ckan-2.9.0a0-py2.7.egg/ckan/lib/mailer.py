# encoding: utf-8

import codecs
import os
import smtplib
import socket
import logging
import uuid
from time import time
from email.mime.text import MIMEText
from email.header import Header
from email import Utils

from ckan.common import config
import paste.deploy.converters
from six import text_type

import ckan
import ckan.model as model
import ckan.lib.helpers as h
from ckan.lib.base import render_jinja2

from ckan.common import _

log = logging.getLogger(__name__)


class MailerException(Exception):
    pass


def _mail_recipient(recipient_name, recipient_email,
                    sender_name, sender_url, subject,
                    body, headers=None):

    if not headers:
        headers = {}

    mail_from = config.get('smtp.mail_from')
    msg = MIMEText(body.encode('utf-8'), 'plain', 'utf-8')
    for k, v in headers.items():
        if k in msg.keys():
            msg.replace_header(k, v)
        else:
            msg.add_header(k, v)
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

    try:
        smtp_connection.connect(smtp_server)
    except socket.error as e:
        log.exception(e)
        raise MailerException('SMTP server could not be connected to: "%s" %s'
                              % (smtp_server, e))
    try:
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

    except smtplib.SMTPException as e:
        msg = '%r' % e
        log.exception(msg)
        raise MailerException(msg)
    finally:
        smtp_connection.quit()


def mail_recipient(recipient_name, recipient_email, subject,
                   body, headers={}):
    site_title = config.get('ckan.site_title')
    site_url = config.get('ckan.site_url')
    return _mail_recipient(recipient_name, recipient_email,
                           site_title, site_url, subject, body,
                           headers=headers)


def mail_user(recipient, subject, body, headers={}):
    if (recipient.email is None) or not len(recipient.email):
        raise MailerException(_("No recipient email address available!"))
    mail_recipient(recipient.display_name, recipient.email, subject,
                   body, headers=headers)


def get_reset_link_body(user):
    extra_vars = {
        'reset_link': get_reset_link(user),
        'site_title': config.get('ckan.site_title'),
        'site_url': config.get('ckan.site_url'),
        'user_name': user.name,
        }
    # NOTE: This template is translated
    return render_jinja2('emails/reset_password.txt', extra_vars)


def get_invite_body(user, group_dict=None, role=None):
    if group_dict:
        group_type = (_('organization') if group_dict['is_organization']
                      else _('group'))

    extra_vars = {
        'reset_link': get_reset_link(user),
        'site_title': config.get('ckan.site_title'),
        'site_url': config.get('ckan.site_url'),
        'user_name': user.name,
        }
    if role:
        extra_vars['role_name'] = h.roles_translated().get(role, _(role))
    if group_dict:
        extra_vars['group_type'] = group_type
        extra_vars['group_title'] = group_dict.get('title')

    # NOTE: This template is translated
    return render_jinja2('emails/invite_user.txt', extra_vars)


def get_reset_link(user):
    return h.url_for(controller='user',
                     action='perform_reset',
                     id=user.id,
                     key=user.reset_key,
                     qualified=True)


def send_reset_link(user):
    create_reset_key(user)
    body = get_reset_link_body(user)
    extra_vars = {
        'site_title': config.get('ckan.site_title')
    }
    subject = render_jinja2('emails/reset_password_subject.txt', extra_vars)

    # Make sure we only use the first line
    subject = subject.split('\n')[0]

    mail_user(user, subject, body)


def send_invite(user, group_dict=None, role=None):
    create_reset_key(user)
    body = get_invite_body(user, group_dict, role)
    extra_vars = {
        'site_title': config.get('ckan.site_title')
    }
    subject = render_jinja2('emails/invite_user_subject.txt', extra_vars)

    # Make sure we only use the first line
    subject = subject.split('\n')[0]

    mail_user(user, subject, body)


def create_reset_key(user):
    user.reset_key = text_type(make_key())
    model.repo.commit_and_remove()


def make_key():
    return codecs.encode(os.urandom(16), 'hex')


def verify_reset_link(user, key):
    if not key:
        return False
    if not user.reset_key or len(user.reset_key) < 5:
        return False
    return key.strip() == user.reset_key
