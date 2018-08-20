# encoding: utf-8

import os

import click
from flask import Flask, current_app
from flask.cli import FlaskGroup, with_appcontext
from werkzeug.serving import run_simple

from ckan.common import config
from ckan.config.middleware import make_app
from ckan.lib.cli import (click_config_option, load_config, parse_db_config,
                          paster_click_group)

# os.environ['FLASK_RUN_FROM_CLI'] = 'true'


def _load_config(config=None):

    # app = make_app
    # app.config.from_file
    # return app
    pass


def _helper():
    print('nothing')


@click.help_option(u'-h', u'--help')
@click_config_option
def run():
    # app = _load_config(config)
    click.echo('Starting CKAN')
    run_simple('localhost', 5000, make_app, use_reloader=True, use_evalex=True)
