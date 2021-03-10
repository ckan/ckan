# encoding: utf-8

import click
import subprocess
import os

import six

from ckan.common import config
from ckan.cli import error_shout


@click.command(
    name=u'less',
    short_help=u'Compile all root less documents into their CSS counterparts')
def less():
    command = (u'npm', u'run', u'build')

    public = config.get(u'ckan.base_public_folder')

    root = os.path.join(os.path.dirname(__file__), u'..', public, u'base')
    root = os.path.abspath(root)
    _compile_less(root, command, u'main')


def _compile_less(root, command, color):
    click.echo(u'compile {}.css'.format(color))
    command = command + (u'--', u'--' + color)

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    output = process.communicate()
    for block in output:
        click.echo(six.ensure_text(block))
