# encoding: utf-8

import os

import click
from flask import Flask, current_app
from werkzeug.serving import run_simple

from ckan.config.middleware import make_app
from ckan.cli import load_config, click_config_option


@click.command(u'run', short_help=u'Start development server')
@click.help_option(u'-h', u'--help')
@click_config_option
@click.option(u'-H', u'--host', default=u'localhost', help=u'Set host')
@click.option(u'-p', u'--port', default=5000, help=u'Set port')
@click.option(u'-r', u'--reloader', default=True, help=u'Use reloader')
def run(config, host, port, reloader):
    u'''Runs development server'''
    conf = load_config(config)
    app = make_app(conf.global_conf, **conf.local_conf)
    run_simple(host, port, app, use_reloader=reloader, use_evalex=True)
