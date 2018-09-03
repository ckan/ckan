# encoding: utf-8

import os

import click


@click.group()
@click.help_option(u'-h', u'--help')
def ckan(*args, **kwargs):
    pass


from ckan.cli.server.server import run
ckan.add_command(run)
