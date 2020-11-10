# encoding: utf-8

import logging

import click
from werkzeug.serving import run_simple

import ckan.plugins.toolkit as tk
from ckan.common import config

log = logging.getLogger(__name__)


@click.command(u"run", short_help=u"Start development server")
@click.option(u"-H", u"--host", default=u"localhost", help=u"Set host")
@click.option(u"-p", u"--port", default=5000, help=u"Set port")
@click.option(u"-r", u"--disable-reloader", is_flag=True,
              help=u"Disable reloader")
@click.option(
    u"-t", u"--threaded", is_flag=True,
    help=u"Handle each request in a separate thread"
)
@click.option(u"-e", u"--extra-files", multiple=True)
@click.option(
    u"--processes", type=int, default=0,
    help=u"Maximum number of concurrent processes"
)
@click.pass_context
def run(ctx, host, port, disable_reloader, threaded, extra_files, processes):
    u"""Runs the Werkzeug development server"""
    use_reloader = not disable_reloader
    threaded = threaded or tk.asbool(config.get(u"ckan.devserver.threaded"))
    processes = processes or tk.asint(
        config.get(u"ckan.devserver.multiprocess", 1)
    )
    if threaded and processes > 1:
        tk.error_shout(u"Cannot have a multithreaded and multi process server")
        raise click.Abort()

    log.info(u"Running server {0} on port {1}".format(host, port))

    config_extra_files = tk.aslist(
        config.get(u"ckan.devserver.watch_patterns")
    )
    extra_files = list(extra_files) + [
        config[u"__file__"]
    ] + config_extra_files

    run_simple(
        host,
        port,
        ctx.obj.app,
        use_reloader=use_reloader,
        use_evalex=True,
        threaded=threaded,
        processes=processes,
        extra_files=extra_files,
    )
