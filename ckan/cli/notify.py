# encoding: utf-8

import click
from ckan.model import Session, Package, DomainObjectOperation
from ckan.model.modification import DomainObjectModificationExtension


@click.group(
    name='notify',
    short_help='Send out modification notifications.'
)
def notify():
    pass


@notify.command(
    name='replay',
    short_help='Send out modification signals.'
)
def replay():
    dome = DomainObjectModificationExtension()
    for package in Session.query(Package):
        dome.notify(package, DomainObjectOperation.changed)
