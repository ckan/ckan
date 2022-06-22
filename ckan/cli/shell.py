# encoding: utf-8
import click

import ckan.model as model

from ckan.plugins import toolkit
from ckan.cli import error_shout


@click.command()
@click.help_option(u'-h', u'--help')
@click.pass_context
def shell(ctx: click.Context):
    '''Run an interactive IPython shell in the context of the
    CKAN instance.

    The following variables will be pre-populated:
     - app (CKAN Application object)
     - config (CKAN config dictionary)
     - model (CKAN model module to access the Database)
     - toolkit (CKAN toolkit module)
    '''
    try:
        from IPython import start_ipython
    except ImportError:
        error_shout("`ipython` library is missing from import path.")
        error_shout("Make sure you have dev-dependencies installed:")
        error_shout("\tpip install -r dev-requirements.txt")
        raise click.Abort()

    namespace = {
        "app": ctx.obj.app._wsgi_app,
        "model": model,
        "config": ctx.obj.config,
        "toolkit": toolkit
        }

    start_ipython([], user_ns=namespace)
