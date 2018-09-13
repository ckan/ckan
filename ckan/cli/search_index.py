# encoding: utf-8

import os

import click
from flask import Flask, current_app
from werkzeug.serving import run_simple

from ckan.cli import click_config_option


@click.group(name=u'search-index', short_help=u'Search index commands')
@click.help_option(u'-h', u'--help')
def search_index():
    pass


@search_index.command(name=u'rebuild', short_help=u'Rebuild search index')
@click.help_option(u'-h', u'--help')
@click.option(u'-v', u'--verbose', is_flag=True)
@click.option(u'-i', u'--force', is_flag=True,
              help=u'Ignore exceptions when rebuilding the index')
@click.option(u'-r', u'--refresh', help=u'Refresh current index', is_flag=True)
@click.option(u'-o', u'--only-missing',
              help=u'Index non indexed datasets only', is_flag=True)
@click.option(u'-q', u'--quiet', help=u'Do not output index rebuild progress',
              is_flag=True)
@click.option(u'-e', u'--commit-each', is_flag=True,
              help=u'Perform a commit after indexing each dataset. This'
                   u'ensures that changes are immediately available on the'
                   u'search, but slows significantly the process. Default'
                   u'is false.')
@click.pass_context
def rebuild(ctx, verbose, force, refresh, only_missing, quiet, commit_each):
    u''' Rebuild search index '''
    from ckan.lib.search import rebuild, commit
    try:
        with ctx.obj.app.apps.get('flask_app').app.app.app.test_request_context():
            rebuild(only_missing=only_missing,
                    force=force,
                    refresh=refresh,
                    defer_commit=(not commit_each),
                    quiet=quiet)
    except Exception as e:
        click.echo(e, err=True)
    if not commit_each:
        commit()
