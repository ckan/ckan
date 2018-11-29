# encoding: utf-8

import os

import click
import logging
from logging.config import fileConfig as loggingFileConfig

log = logging.getLogger(__name__)


def error_shout(exception):
    click.secho(str(exception), fg=u'red', err=True)


click_config_option = click.option(
    u'-c',
    u'--config',
    default=None,
    metavar=u'CONFIG',
    help=u'Config file to use (default: development.ini)'
)


def load_config(config=None):
    from paste.deploy import appconfig
    if config:
        filename = os.path.abspath(config)
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
