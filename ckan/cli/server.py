# encoding: utf-8

import logging

import click
from werkzeug.serving import run_simple

import ckan.plugins.toolkit as tk
from ckan.common import config

log = logging.getLogger(__name__)

DEFAULT_HOST = u"localhost"
DEFAULT_PORT = 5000


@click.command(u"run", short_help=u"Start development server")
@click.option(u"-H", u"--host", help=u"Host name")
@click.option(u"-p", u"--port", help=u"Port number")
@click.option(u"-r", u"--disable-reloader", is_flag=True,
              help=u"Disable reloader")
@click.option(u"-E", u"--passthrough-errors", is_flag=True,
              help=u"Disable error caching (useful to hook debuggers)")
@click.option(
    u"-t", u"--threaded", is_flag=True,
    help=u"Handle each request in a separate thread"
)
@click.option(
    u"--processes", type=int, default=0,
    help=u"Maximum number of concurrent processes"
)
@click.option(
    u"-e", u"--extra-files", multiple=True,
    help=u"Additional files that should be watched for server reloading"
    " (you can provide multiple values)")
@click.option(
    u"-C", u"--ssl-cert", default=None,
    help=u"Certificate file to use to enable SSL. Passing 'adhoc' will "
    " automatically generate a new one (on each server reload).")
@click.option(
    u"-K", u"--ssl-key", default=None,
    help=u"Key file to use to enable SSL. Passing 'adhoc' will "
    " automatically generate a new one (on each server reload).")
@click.pass_context
def run(ctx, host, port, disable_reloader, passthrough_errors, threaded,
        extra_files, processes, ssl_cert, ssl_key):
    u"""Runs the Werkzeug development server"""

    # passthrough_errors overrides conflicting options
    if passthrough_errors:
        disable_reloader = True
        threaded = False
        processes = 1

    # Reloading
    use_reloader = not disable_reloader
    config_extra_files = tk.aslist(
        config.get(u"ckan.devserver.watch_patterns")
    )
    extra_files = list(extra_files) + [
        config[u"__file__"]
    ] + config_extra_files

    # Threads and processes
    threaded = threaded or tk.asbool(config.get(u"ckan.devserver.threaded"))
    processes = processes or tk.asint(
        config.get(u"ckan.devserver.multiprocess", 1)
    )
    if threaded and processes > 1:
        tk.error_shout(u"Cannot have a multithreaded and multi process server")
        raise click.Abort()

    # SSL
    cert_file = ssl_cert or config.get(u"ckan.devserver.ssl_cert")
    key_file = ssl_key or config.get(u"ckan.devserver.ssl_key")

    if cert_file and key_file:
        if cert_file == key_file == u"adhoc":
            ssl_context = u"adhoc"
        else:
            ssl_context = (ssl_cert, ssl_key)
    else:
        ssl_context = None

    host = host or config.get(u'ckan.devserver.host', DEFAULT_HOST)
    port = port or config.get(u'ckan.devserver.port', DEFAULT_PORT)
    try:
        port = int(port)
    except ValueError:
        tk.error_shout(u"Server port must be an integer, not {}".format(port))
        raise click.Abort()

    log.info(u"Running CKAN on {scheme}://{host}:{port}".format(
        scheme=u"https" if ssl_context else u"http", host=host, port=port))

    run_simple(
        host,
        port,
        ctx.obj.app,
        use_reloader=use_reloader,
        use_evalex=True,
        threaded=threaded,
        processes=processes,
        extra_files=extra_files,
        ssl_context=ssl_context,
        passthrough_errors=passthrough_errors,
    )
