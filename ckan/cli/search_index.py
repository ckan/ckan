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
@click.option(u'-i', u'--force', is_flag=True,
              help=u'Ignore exceptions when rebuilding the index')
@click.option(u'-r', u'--refresh')
@click.option(u'-o', u'--only-missing')
def rebuild(force, only_missing):
    ''' Rebuild search index '''
    from ckan.lib.search import rebuild, commit
    # if force:
    #   rebuild()
