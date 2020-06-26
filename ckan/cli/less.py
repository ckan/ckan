# encoding: utf-8

import click
import subprocess
import os

import six

from ckan.common import config
from ckan.cli import error_shout


_custom_css = {
    u'fuchsia': u'''
        @layoutLinkColor: #E73892;
        @footerTextColor: mix(#FFF, @layoutLinkColor, 60%);
        @footerLinkColor: @footerTextColor;
        @mastheadBackgroundColor: @layoutLinkColor;
        @btnPrimaryBackground: lighten(@layoutLinkColor, 10%);
        @btnPrimaryBackgroundHighlight: @layoutLinkColor;
        ''',

    u'green': u'''
        @layoutLinkColor: #2F9B45;
        @footerTextColor: mix(#FFF, @layoutLinkColor, 60%);
        @footerLinkColor: @footerTextColor;
        @mastheadBackgroundColor: @layoutLinkColor;
        @btnPrimaryBackground: lighten(@layoutLinkColor, 10%);
        @btnPrimaryBackgroundHighlight: @layoutLinkColor;
        ''',

    u'red': u'''
        @layoutLinkColor: #C14531;
        @footerTextColor: mix(#FFF, @layoutLinkColor, 60%);
        @footerLinkColor: @footerTextColor;
        @mastheadBackgroundColor: @layoutLinkColor;
        @btnPrimaryBackground: lighten(@layoutLinkColor, 10%);
        @btnPrimaryBackgroundHighlight: @layoutLinkColor;
        ''',

    u'maroon': u'''
        @layoutLinkColor: #810606;
        @footerTextColor: mix(#FFF, @layoutLinkColor, 60%);
        @footerLinkColor: @footerTextColor;
        @mastheadBackgroundColor: @layoutLinkColor;
        @btnPrimaryBackground: lighten(@layoutLinkColor, 10%);
        @btnPrimaryBackgroundHighlight: @layoutLinkColor;
        ''',
}


@click.command(
    name=u'less',
    short_help=u'Compile all root less documents into their CSS counterparts')
def less():
    command = (u'npm', u'run', u'build')

    public = config.get(u'ckan.base_public_folder')

    root = os.path.join(os.path.dirname(__file__), u'..', public, u'base')
    root = os.path.abspath(root)
    custom_less = os.path.join(root, u'less', u'custom.less')
    for color in _custom_css:
        f = open(custom_less, u'w')
        f.write(_custom_css[color])
        f.close()
        _compile_less(root, command, color)
    f = open(custom_less, u'w')
    f.write(u'// This file is needed in order for `gulp build` to '
            u'compile in less 1.3.1+\n')
    f.close()
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
