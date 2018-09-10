# encoding: utf-8

import os

import click
from flask import Flask, current_app
from werkzeug.serving import run_simple

from ckan.cli import load_config, click_config_option


@click.command(u'run', short_help=u'Start development server')
@click.help_option(u'-h', u'--help')
@click_config_option
@click.option(u'-H', u'--host', default=u'localhost', help=u'Set host')
@click.option(u'-p', u'--port', default=5000, help=u'Set port')
@click.option(u'-r', u'--reloader', default=True, help=u'Use reloader')
@click.pass_context
def run(ctx, config, host, port, reloader):
    u'''Runs development server'''
    run_simple(host, port, ctx.obj.app, use_reloader=reloader, use_evalex=True)
