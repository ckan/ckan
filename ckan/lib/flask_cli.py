# encoding: utf-8

import os

import click
from flask import Flask, current_app
from flask.cli import AppGroup, with_appcontext
from werkzeug.serving import run_simple

from ckan.common import config
from ckan.config.environment import load_environment

from ckan.config.middleware import make_app
from ckan.lib.cli import (click_config_option, load_config, parse_db_config,
                          paster_click_group)

# os.environ['FLASK_RUN_FROM_CLI'] = 'true'


def _load_config(config=None):

    from paste.deploy import appconfig
    from paste.script.util.logging_config import fileConfig

    if config:
        filename = os.path.abspath(config)
        config_source = u'-c parameter'
    elif os.environ.get(u'CKAN_INI'):
        filename = os.environ.get(u'CKAN_INI')
        config_source = u'$CKAN_INI'
    else:
        default_filename = u'development.ini'
        filename = os.path.join(os.getcwd(), default_filename)
        if not os.path.exists(filename):
            # give really clear error message for this common situation
            msg = u'ERROR: You need to specify the CKAN config (.ini) '\
                u'file path.'\
                u'\nUse the --config parameter or set environment ' \
                u'variable CKAN_INI or have {}\nin the current directory.' \
                .format(default_filename)
            exit(msg)

    if not os.path.exists(filename):
        msg = u'Config file not found: %s' % filename
        msg += u'\n(Given by: %s)' % config_source
        exit(msg)

    fileConfig(filename)
    return appconfig(u'config:' + filename)


@click.group()
@click.help_option(u'-h', u'--help')
def main(*args, **kwargs):
    pass


@main.command(u'run', short_help=u'Start development server')
@click.help_option(u'-h', u'--help')
@click_config_option
@click.option(u'-H', u'--host', default=u'localhost', help=u'Set host')
@click.option(u'-p', u'--port', default=5000, help=u'Set port')
@click.option(u'-r', u'--reloader', default=True, help=u'Use reloader')
def run(config, host, port, reloader):
    u'''Runs development server'''
    conf = _load_config(config)
    app = make_app(conf.global_conf, **conf.local_conf)
    run_simple(host, port, app, use_reloader=reloader, use_evalex=True)


@main.command(u'db', short_help=u'Initialize the database')
@click.help_option(u'-h', u'--help')
@click_config_option
@click.argument(u'init')
def initdb(config, init):
    u'''Initialising the database'''
    conf = _load_config(config)
    load_environment(conf.global_conf, conf.local_conf)
    try:
        import ckan.model as model
        model.repo.init_db()
    except Exception as e:
        print e
    print(u'Initialising DB: SUCCESS')
