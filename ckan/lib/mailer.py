# encoding: utf-8
from __future__ import annotations

import codecs
import os
import smtplib
import socket
import logging
import mimetypes
from time import time
from typing import Any, Iterable, Optional, Tuple, Union, IO, cast

from email.message import EmailMessage
from email import utils

from ckan.common import _, config


import ckan
import ckan.model as model
import ckan.lib.helpers as h
from ckan.lib.base import render

log = logging.getLogger(__name__)
AttachmentWithType = Union[
    Tuple[str, IO[str], str],
    Tuple[str, IO[bytes], str]
]
AttachmentWithoutType = Union[Tuple[str, IO[str]], Tuple[str, IO[bytes]]]
Attachment = Union[AttachmentWithType, AttachmentWithoutType]


class MailerException(Exception):
    pass


def _mail_recipient(
        recipient_name: str, recipient_email: str, sender_name: str,
        sender_url: str, subject: Any, body: Any,
        body_html: Optional[Any] = None,
        headers: Optional[dict[str, Any]] = None,
        attachments: Optional[Iterable[Attachment]] = None) -> None:

    if not headers:
        headers = {}

    if not attachments:
        attachments = []

    mail_from = config.get('smtp.mail_from')

    reply_to = config.get('smtp.reply_to')

    msg = EmailMessage()

    msg.set_content(body, cte='base64')

    if body_html:
        msg.add_alternative(body_html, subtype='html', cte='base64')

    for k, v in headers.items():
        if k in msg.keys():
            msg.replace_header(k, v)
        else:
            msg.add_header(k, v)
    msg['Subject'] = subject
    msg['From'] = utils.formataddr((sender_name, mail_from))
    msg['To'] = utils.formataddr((recipient_name, recipient_email))
    msg['Date'] = utils.formatdate(time())
    if not config.get('ckan.hide_version'):
        msg['X-Mailer'] = "CKAN %s" % ckan.__version__
    # Check if extension is setting reply-to via headers or use config option
    if reply_to and reply_to != '' and not msg['Reply-to']:
        msg['Reply-to'] = reply_to

    for attachment in attachments:
        if len(attachment) == 3:
            name, _file, media_type = cast(AttachmentWithType, attachment)
        else:
            name, _file = cast(AttachmentWithoutType, attachment)
            media_type = None

        if not media_type:
            media_type, _encoding = mimetypes.guess_type(name)
        if media_type:
            main_type, sub_type = media_type.split('/')
        else:
            main_type = sub_type = None

        msg.add_attachment(
            _file.read(), filename=name, maintype=main_type, subtype=sub_type)

    # Send the email using Python's smtplib.
    smtp_server = config.get('smtp.server')
    smtp_starttls = config.get('smtp.starttls')
    smtp_user = config.get('smtp.user')
    smtp_password = config.get('smtp.password')

    try:
        smtp_connection = smtplib.SMTP(smtp_server)
    except (socket.error, smtplib.SMTPConnectError) as e:
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


def mail_recipient(recipient_name: str,
                   recipient_email: str,
                   subject: str,
                   body: str,
                   body_html: Optional[str] = None,
                   headers: Optional[dict[str, Any]] = None,
                   attachments: Optional[Iterable[Attachment]] = None) -> None:

    '''Sends an email to a an email address.

    .. note:: You need to set up the :ref:`email-settings` to able to send
        emails.

    :param recipient_name: the name of the recipient
    :type recipient: string
    :param recipient_email: the email address of the recipient
    :type recipient: string

    :param subject: the email subject
    :type subject: string
    :param body: the email body, in plain text
    :type body: string
    :param body_html: the email body, in html format (optional)
    :type body_html: string
    :headers: extra headers to add to email, in the form
        {'Header name': 'Header value'}
    :type: dict
    :attachments: a list of tuples containing file attachments to add to the
        email. Tuples should contain the file name and a file-like object
        pointing to the file contents::

            [
                ('some_report.csv', file_object),
            ]

        Optionally, you can add a third element to the tuple containing the
        media type. If not provided, it will be guessed using
        the ``mimetypes`` module::

            [
                ('some_report.csv', file_object, 'text/csv'),
            ]
    :type: list
    '''
    site_title = config.get('ckan.site_title')
    site_url = config.get('ckan.site_url')
    return _mail_recipient(
        recipient_name, recipient_email,
        site_title, site_url, subject, body,
        body_html=body_html, headers=headers, attachments=attachments)


def mail_user(recipient: model.User,
              subject: str,
              body: str,
              body_html: Optional[str] = None,
              headers: Optional[dict[str, Any]] = None,
              attachments: Optional[Iterable[Attachment]] = None) -> None:
    '''Sends an email to a CKAN user.

    You need to set up the :ref:`email-settings` to able to send emails.

    :param recipient: a CKAN user object
    :type recipient: a model.User object

    For further parameters see
    :py:func:`~ckan.lib.mailer.mail_recipient`.
    '''

    if (recipient.email is None) or not len(recipient.email):
        raise MailerException(_("No recipient email address available!"))
    mail_recipient(
        recipient.display_name, recipient.email, subject,
        body, body_html=body_html, headers=headers, attachments=attachments)


def get_reset_link_body(user: model.User) -> str:
    extra_vars = {
        'reset_link': get_reset_link(user),
        'site_title': config.get('ckan.site_title'),
        'site_url': config.get('ckan.site_url'),
        'user_name': user.name,
    }
    # NOTE: This template is translated
    return render('emails/reset_password.txt', extra_vars)


def get_invite_body(user: model.User,
                    group_dict: Optional[dict[str, Any]] = None,
                    role: Optional[str] = None) -> str:
    extra_vars = {
        'reset_link': get_reset_link(user),
        'site_title': config.get('ckan.site_title'),
        'site_url': config.get('ckan.site_url'),
        'user_name': user.name,
    }

    if role:
        extra_vars['role_name'] = h.roles_translated().get(role, _(role))
    if group_dict:
        group_type = (_('organization') if group_dict['is_organization']
                      else _('group'))
        extra_vars['group_type'] = group_type
        extra_vars['group_title'] = group_dict.get('title')

    # NOTE: This template is translated
    return render('emails/invite_user.txt', extra_vars)


def get_reset_link(user: model.User) -> str:
    return h.url_for('user.perform_reset',
                     id=user.id,
                     key=user.reset_key,
                     qualified=True)


def send_reset_link(user: model.User) -> None:
    create_reset_key(user)
    body = get_reset_link_body(user)
    extra_vars = {
        'site_title': config.get('ckan.site_title')
    }
    subject = render('emails/reset_password_subject.txt', extra_vars)

    # Make sure we only use the first line
    subject = subject.split('\n')[0]

    mail_user(user, subject, body)


def send_invite(
        user: model.User,
        group_dict: Optional[dict[str, Any]] = None,
        role: Optional[str] = None) -> None:
    create_reset_key(user)
    body = get_invite_body(user, group_dict, role)
    extra_vars = {
        'site_title': config.get('ckan.site_title')
    }
    subject = render('emails/invite_user_subject.txt', extra_vars)

    # Make sure we only use the first line
    subject = subject.split('\n')[0]

    mail_user(user, subject, body)


def create_reset_key(user: model.User):
    user.reset_key = make_key()
    model.repo.commit_and_remove()


def make_key():
    return codecs.encode(os.urandom(16), 'hex').decode()


def verify_reset_link(user: model.User, key: Optional[str]) -> bool:
    if not key:
        return False
    if not user.reset_key or len(user.reset_key) < 5:
        return False
    return key.strip() == user.reset_key
