# encoding: utf-8

import os

import click
from ckan.cli import db, server


@click.group()
@click.help_option(u'-h', u'--help')
def ckan(*args, **kwargs):
    pass


ckan.add_command(server.run)
ckan.add_command(db.db)
