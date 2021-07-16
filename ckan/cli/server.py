# encoding: utf-8

import logging

import click
from werkzeug.serving import run_simple

import ckan.plugins.toolkit as tk
from ckan.common import config

log = logging.getLogger(__name__)

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 5000


@click.command("run", short_help="Start development server")
@click.option("-H", "--host", help="Host name")
@click.option("-p", "--port", help="Port number")
@click.option("-r", "--disable-reloader", is_flag=True,
              help="Disable reloader")
@click.option(
    "-t", "--threaded", is_flag=True,
    help="Handle each request in a separate thread"
)
@click.option(
    "--processes", type=int, default=0,
    help="Maximum number of concurrent processes"
)
@click.option(
    "-e", "--extra-files", multiple=True,
    help="Additional files that should be watched for server reloading"
    " (you can provide multiple values)")
@click.option(
    "-C", "--ssl-cert", default=None,
    help="Certificate file to use to enable SSL. Passing 'adhoc' will "
    " automatically generate a new one (on each server reload).")
@click.option(
    "-K", "--ssl-key", default=None,
    help="Key file to use to enable SSL. Passing 'adhoc' will "
    " automatically generate a new one (on each server reload).")
@click.pass_context
def run(ctx, host, port, disable_reloader, threaded, extra_files, processes,
        ssl_cert, ssl_key):
    """Runs the Werkzeug development server"""

    # Reloading
    use_reloader = not disable_reloader
    config_extra_files = tk.aslist(
        config.get("ckan.devserver.watch_patterns")
    )
    extra_files = list(extra_files) + [
        config["__file__"]
    ] + config_extra_files

    # Threads and processes
    threaded = threaded or tk.asbool(config.get("ckan.devserver.threaded"))
    processes = processes or tk.asint(
        config.get("ckan.devserver.multiprocess", 1)
    )
    if threaded and processes > 1:
        tk.error_shout("Cannot have a multithreaded and multi process server")
        raise click.Abort()

    # SSL
    cert_file = ssl_cert or config.get('ckan.devserver.ssl_cert')
    key_file = ssl_key or config.get('ckan.devserver.ssl_key')

    if cert_file and key_file:
        if cert_file == key_file == 'adhoc':
            ssl_context = 'adhoc'
        else:
            ssl_context = (ssl_cert, ssl_key)
    else:
        ssl_context = None

    host = host or config.get('ckan.devserver.host', DEFAULT_HOST)
    port = port or config.get('ckan.devserver.port', DEFAULT_PORT)
    try:
        port = int(port)
    except ValueError:
        tk.error_shout("Server port must be an integer, not {}".format(port))
        raise click.Abort()

    log.info("Running CKAN on {scheme}://{host}:{port}".format(
        scheme='https' if ssl_context else 'http', host=host, port=port))

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
    )
