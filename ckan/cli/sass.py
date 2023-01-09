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
@click.option(u"-d", u"--debug", is_flag=True)
def sass(debug: bool):
    command = (u'npm', u'run', u'build')

    public = config.get_value(u'ckan.base_public_folder')

    root = os.path.join(os.path.dirname(__file__), u'..', public, u'base')
    root = os.path.abspath(root)
    _compile_sass(root, command, u'main', debug)


def _compile_sass(root: str, command: tuple[str, ...], color: str, debug: bool):
    click.echo(u'compile {}.css'.format(color))
    command = command + (u'--', u'--' + color)
    if debug:
        command = command + (u'--debug',)

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    output = process.communicate()
    for block in output:
        click.echo(six.ensure_text(block))
