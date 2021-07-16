# encoding: utf-8

import click
import subprocess
import os

import six

from ckan.common import config


@click.command(
    name='less',
    short_help='Compile all root less documents into their CSS counterparts')
def less():
    command = ('npm', 'run', 'build')

    public = config.get('ckan.base_public_folder')

    root = os.path.join(os.path.dirname(__file__), '..', public, 'base')
    root = os.path.abspath(root)
    _compile_less(root, command, 'main')


def _compile_less(root, command, color):
    click.echo('compile {}.css'.format(color))
    command = command + ('--', '--' + color)

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    output = process.communicate()
    for block in output:
        click.echo(six.ensure_text(block))
