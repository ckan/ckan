# encoding: utf-8
from __future__ import annotations

import subprocess
import os

import click
import six

from ckan.common import config


@click.command(
    name=u'sass',
    short_help=u'Compile all root sass documents into their CSS counterparts')
def sass():
    command = (u'npm', u'run', u'build')

    public = config.get_value(u'ckan.base_public_folder')

    root = os.path.join(os.path.dirname(__file__), u'..', public, u'base')
    root = os.path.abspath(root)
    _compile_sass(root, command, u'main')


def _compile_sass(root: str, command: tuple[str, ...], color: str):
    click.echo(u'compile {}.css'.format(color))
    command = command + (u'--', u'--' + color)

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    output = process.communicate()
    for block in output:
        click.echo(six.ensure_text(block))
