# encoding: utf-8
import click

import ckan.model as model

from IPython import start_ipython


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
    '''
    namespace = {
        "app": ctx.obj.app._wsgi_app,
        "model": model,
        "config": ctx.obj.config
        }

    start_ipython([], user_ns=namespace)
