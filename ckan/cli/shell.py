# encoding: utf-8
import click

import ckan.model as model

from ckan.plugins import toolkit
from ckan.cli import error_shout


@click.command()
@click.help_option("-h", "--help")
@click.pass_context
def shell(ctx: click.Context):
    """Run an interactive IPython shell with the context of the
    CKAN instance.
    """
    try:
        from IPython import start_ipython  # type: ignore
        from traitlets.config.loader import Config
    except ImportError:
        error_shout("`ipython` library is missing from import path.")
        error_shout("Make sure you have dev-dependencies installed:")
        error_shout("\tpip install -r dev-requirements.txt")
        raise click.Abort()

    c = Config()
    banner = """
****** Welcome to the CKAN shell ******

This IPython session has some variables pre-populated:
  - app (CKAN Application object)
  - config (CKAN config dictionary)
  - model (CKAN model module to access the Database)
  - toolkit (CKAN toolkit module)
    """
    c.TerminalInteractiveShell.banner2 = banner  # type: ignore

    namespace = {
        "app": ctx.obj.app._wsgi_app,
        "model": model,
        "config": ctx.obj.config,
        "toolkit": toolkit,
    }

    start_ipython([], user_ns=namespace, config=c)
