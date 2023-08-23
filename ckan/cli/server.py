# encoding: utf-8
from __future__ import annotations

from ckan.exceptions import CkanDeprecationWarning
import logging
import warnings
from typing import Optional

import click
from werkzeug.serving import run_simple
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from ckan.common import config
from . import error_shout

log = logging.getLogger(__name__)

DEFAULT_HOST = "localhost"
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
@click.option(
    u"-P", u"--prefix", default="",
    help=u"Run ckan in prefix path."
)
@click.pass_context
def run(ctx: click.Context, host: str, port: str, disable_reloader: bool,
        passthrough_errors: bool, threaded: bool, extra_files: list[str],
        processes: int, ssl_cert: Optional[str], ssl_key: Optional[str],
        prefix: Optional[str]):
    u"""Runs the Werkzeug development server"""

    if config.get("debug"):
        warnings.filterwarnings("default", category=CkanDeprecationWarning)

    # passthrough_errors overrides conflicting options
    if passthrough_errors:
        disable_reloader = True
        threaded = False
        processes = 1

    # Reloading
    use_reloader = not disable_reloader
    config_extra_files = config.get(u"ckan.devserver.watch_patterns")
    extra_files = list(extra_files) + [
        config[u"__file__"]
    ] + config_extra_files

    # Threads and processes
    threaded = threaded or config.get(u"ckan.devserver.threaded")
    processes = processes or config.get(u"ckan.devserver.multiprocess")
    if threaded and processes > 1:
        error_shout(u"Cannot have a multithreaded and multi process server")
        raise click.Abort()

    # SSL
    cert_file = ssl_cert or config.get('ckan.devserver.ssl_cert')
    key_file = ssl_key or config.get('ckan.devserver.ssl_key')

    if cert_file and key_file:
        if cert_file == key_file == 'adhoc':
            ssl_context = 'adhoc'
        else:
            ssl_context = (cert_file, key_file)
    else:
        ssl_context = None

    if prefix:
        if not prefix.startswith(u'/'):
            error_shout(u"Prefix must start with /, example /data.")
            raise click.Abort()
        ctx.obj.app = DispatcherMiddleware(ctx.obj.app, {
            prefix: ctx.obj.app
        })

    host = host or config.get('ckan.devserver.host')
    port = port or config.get('ckan.devserver.port')
    try:
        port_int = int(port)
    except ValueError:
        error_shout(u"Server port must be an integer, not {}".format(port))
        raise click.Abort()

    log.info(u"Running CKAN on {scheme}://{host}:{port}{prefix}".format(
        scheme='https' if ssl_context else 'http', host=host, port=port_int,
        prefix=prefix))

    run_simple(
        host,
        port_int,
        ctx.obj.app,
        use_reloader=use_reloader,
        use_evalex=True,
        threaded=threaded,
        processes=processes,
        extra_files=extra_files,
        ssl_context=ssl_context,
        passthrough_errors=passthrough_errors,
    )
