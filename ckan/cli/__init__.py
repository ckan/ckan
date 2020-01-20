# encoding: utf-8

import os

import six
import click
import logging
from logging.config import fileConfig as loggingFileConfig

import ckan.plugins as p
from ckan.config.middleware import make_app


log = logging.getLogger(__name__)


def error_shout(exception):
    click.secho(str(exception), fg=u'red', err=True)


class CkanCommand(object):

    def __init__(self, conf=None):
        self.config = load_config(conf)
        self.app = make_app(self.config.global_conf, **self.config.local_conf)


def _init_ckan_config(ctx, param, value):
    ctx.obj = CkanCommand(value)
    if six.PY2:
        ctx.meta["flask_app"] = ctx.obj.app.apps["flask_app"]._wsgi_app
    else:
        ctx.meta["flask_app"] = ctx.obj.app._wsgi_app

    for plugin in p.PluginImplementations(p.IClick):
        for cmd in plugin.get_commands():
            cmd._ckanext = plugin.name
            ctx.command.add_command(cmd)


click_config_option = click.option(
    u'-c',
    u'--config',
    default=None,
    metavar=u'CONFIG',
    help=u'Config file to use (default: development.ini)',
    is_eager=True,
    callback=_init_ckan_config
)


def load_config(ini_path=None):
    from paste.deploy import appconfig

    if ini_path:
        if ini_path.startswith(u'~'):
            ini_path = os.path.expanduser(ini_path)
        filename = os.path.abspath(ini_path)
        config_source = u'-c parameter'
    elif os.environ.get(u'CKAN_INI'):
        filename = os.environ.get(u'CKAN_INI')
        config_source = u'$CKAN_INI'
    else:
        default_filename = u'development.ini'
        filename = os.path.join(os.getcwd(), default_filename)
        if not os.path.exists(filename):
            # give really clear error message for this common situation
            msg = u'ERROR: You need to specify the CKAN config (.ini) '\
                u'file path.'\
                u'\nUse the --config parameter or set environment ' \
                u'variable CKAN_INI or have {}\nin the current directory.' \
                .format(default_filename)
            exit(msg)

    if not os.path.exists(filename):
        msg = u'Config file not found: %s' % filename
        msg += u'\n(Given by: %s)' % config_source
        exit(msg)

    loggingFileConfig(filename)
    log.info(u'Using configuration file {}'.format(filename))
    return appconfig(u'config:' + filename)
