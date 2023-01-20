# encoding: utf-8
from __future__ import annotations

import subprocess
import os

import click
import six

from ckan.common import config


@click.command(
    name='sass',
    short_help='Compile all root sass documents into their CSS counterparts')
@click.option(
    '-d',
    '--debug',
    is_flag=True,
    help="Compile css with sourcemaps.")
def sass(debug: bool):
    command = ('npm', 'run', 'build')

    public = config.get('ckan.base_public_folder')

    root = os.path.join(os.path.dirname(__file__), '..', public, 'base')
    root = os.path.abspath(root)
    _compile_sass(root, command, 'main', debug)


def _compile_sass(
        root: str,
        command: tuple[str, ...],
        color: str,
        debug: bool):
    click.echo('compile {}.css'.format(color))
    command = command + ('--', '--' + color)
    if debug:
        command = command + ('--debug',)

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    output = process.communicate()
    for block in output:
        click.echo(six.ensure_text(block))
