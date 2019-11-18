# encoding: utf-8

import os

import click

from ckan.cli import minify, less, translation
import ckan.plugins.toolkit as toolkit


@click.group(
    name=u"front-end-build",
    short_help=u"Creates and minifies css and JavaScript files.",
    invoke_without_command=True,
)
@click.pass_context
def front_end_build(ctx):
    if ctx.invoked_subcommand is None:
        ctx.invoke(build)


@front_end_build.command(short_help=u"Compile css and js.",)
@click.pass_context
def build(ctx):
    ctx.invoke(less.less)
    ctx.invoke(translation.js)

    # minification
    public = toolkit.config.get(u"ckan.base_public_folder")
    root = os.path.join(os.path.dirname(__file__), u"..", public, u"base")
    root = os.path.abspath(root)
    ckanext = os.path.join(os.path.dirname(__file__), u"..", u"..", u"ckanext")
    ckanext = os.path.abspath(ckanext)
    cmd = ctx.invoke(minify.minify, path=(root, ckanext))
