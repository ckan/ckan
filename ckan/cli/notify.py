# encoding: utf-8

from logging import getLogger
import click
from ckan.model import Session, Package, DomainObjectOperation
from ckan.model.modification import DomainObjectModificationExtension
from ckan.views.resource import NotAuthorized, ValidationError


log = getLogger(__name__)


@click.group(
    name=u'notify',
    short_help=u'Send out modification notifications.'
)
def notify():
    pass


@notify.command(
    name=u'replay',
    short_help=u'Send out modification signals.'
)
def replay():
    dome = DomainObjectModificationExtension()
    breakpoint()
    for package in Session.query(Package):
        dome.notify(package, DomainObjectOperation.changed)


@notify.command(
    name='send_emails',
    short_help='Send out Email notifications.'
)
@click.pass_context
def send_emails(ctx: click.Context):
    import ckan.logic as logic
    import ckan.model as model
    import ckan.lib.mailer as mailer
    from ckan.types import Context
    from typing import cast


    flask_app = ctx.meta['flask_app']
    site_user = logic.get_action(u"get_site_user")({u"ignore_auth": True}, {})
    context = cast(Context, {u"user": site_user[u"name"], 'model': model, 'session': model.Session,})
    with flask_app.test_request_context():
        try:
            logic.get_action('send_email_notifications')(context, {})
        except (NotAuthorized, ValidationError, mailer.MailerException) as e:
            log.error(e)