# encoding: utf-8

import os

import click
from flask import Flask, current_app
from flask.cli import AppGroup, with_appcontext
from werkzeug.serving import run_simple

from ckan.common import config
from ckan.config.middleware import make_app
from ckan.lib.cli import (click_config_option, load_config, parse_db_config,
                          paster_click_group)

# os.environ['FLASK_RUN_FROM_CLI'] = 'true'


def _load_config(config=None):

    from paste.deploy import appconfig
    from paste.script.util.logging_config import fileConfig

    if config:
        filename = os.path.abspath(config)
        config_source = '-c parameter'
    elif os.environ.get('CKAN_INI'):
        filename = os.environ.get('CKAN_INI')
        config_source = '$CKAN_INI'
    else:
        default_filename = 'development.ini'
        filename = os.path.join(os.getcwd(), default_filename)
        if not os.path.exists(filename):
            # give really clear error message for this common situation
            msg = 'ERROR: You need to specify the CKAN config (.ini) '\
                'file path.'\
                '\nUse the --config parameter or set environment ' \
                'variable CKAN_INI or have {}\nin the current directory.' \
                .format(default_filename)
            exit(msg)

    if not os.path.exists(filename):
        msg = 'Config file not found: %s' % filename
        msg += '\n(Given by: %s)' % config_source
        exit(msg)

    fileConfig(filename)
    return appconfig('config:' + filename)


@click.group()
@click.help_option(u'-h', u'--help')
@click.pass_context
def main(*args, **kwargs):
    pass


@click.help_option(u'-h', u'--help')
@main.command(u'run', short_help=u'Start development server')
@click_config_option
@click.option(u'-p', u'--port', default=5000, help=u'Set port')
@click.option(u'-r', u'--reloader', default=True, help=u'Use reloader')
def run(config, port, reloader):
    # click.echo(u'Starting CKAN')
    conf = _load_config(config)
    app = make_app(conf.global_conf, **conf.local_conf)
    run_simple(u'localhost', port, app, use_reloader=reloader, use_evalex=True)
