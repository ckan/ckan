# encoding: utf-8

import click
from ckan.model import Session, Package, DomainObjectOperation
from ckan.model.modification import DomainObjectModificationExtension


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
    for package in Session.query(Package):
        dome.notify(package, DomainObjectOperation.changed)
