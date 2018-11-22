# encoding: utf-8

import logging

import click
from werkzeug.serving import run_simple

log = logging.getLogger(__name__)


@click.command(u'run', short_help=u'Start development server')
@click.option(u'-H', u'--host', default=u'localhost', help=u'Set host')
@click.option(u'-p', u'--port', default=5000, help=u'Set port')
@click.option(u'-r', u'--reloader', default=True, help=u'Use reloader')
@click.pass_context
def run(ctx, host, port, reloader):
    u'''Runs development server'''
    log.info(u"Running server {0} on port {1}".format(host, port))
    run_simple(host, port, ctx.obj.app, use_reloader=reloader, use_evalex=True)
