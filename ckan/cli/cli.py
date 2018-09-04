# encoding: utf-8

import os

import click
from ckan.cli.server.server import run
from ckan.cli.database.db import db


@click.group()
@click.help_option(u'-h', u'--help')
def ckan(*args, **kwargs):
    pass

ckan.add_command(run)
ckan.add_command(db)
