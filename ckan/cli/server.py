# encoding: utf-8

import logging

import click
from werkzeug.serving import run_simple

from ckan.common import config
import ckan.plugins.toolkit as tk

log = logging.getLogger(__name__)


@click.command(u"run", short_help=u"Start development server")
@click.option(u"-H", u"--host", default=u"localhost", help=u"Set host")
@click.option(u"-p", u"--port", default=5000, help=u"Set port")
@click.option(u"-r", u"--reloader", default=True, help=u"Use reloader")
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
def run(ctx, host, port, reloader, threaded, extra_files, processes):
    u"""Runs the Werkzeug development server"""
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
        use_reloader=reloader,
        use_evalex=True,
        threaded=threaded,
        processes=processes,
        extra_files=extra_files,
    )
