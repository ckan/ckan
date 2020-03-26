# encoding: utf-8

import os

import click
import logging
from logging.config import fileConfig as loggingFileConfig
from configparser import ConfigParser


log = logging.getLogger(__name__)


class CKANConfigLoader(object):
    def __init__(self, filename):
        self.config_file = filename.strip()
        self.config = dict()
        self.parser = ConfigParser()
        self.section = u'app:main'
        defaults = {u'__file__': os.path.abspath(self.config_file)}
        self._update_defaults(defaults)
        self._create_config_object()

    def _update_defaults(self, new_defaults):
        for key, value in new_defaults.items():
            self.parser._defaults[key] = value

    def _read_config_file(self, filename):
        defaults = {u'here': os.path.dirname(os.path.abspath(filename))}
        self._update_defaults(defaults)
        self.parser.read(filename)

    def _update_config(self):
        options = self.parser.options(self.section)
        for option in options:
            if option not in self.config or option in self.parser.defaults():
                value = self.parser.get(self.section, option)
                self.config[option] = value
                if option in self.parser.defaults():
                    self.config[u'global_conf'][option] = value

    def _create_config_object(self):
        self._read_config_file(self.config_file)

        # # The global_config key is to keep compatibility with Pylons.
        # # It can be safely removed when the Flask migration is completed.
        self.config[u'global_conf'] = self.parser.defaults().copy()

        self._update_config()

        schema, path = self.parser.get(self.section, u'use').split(u':')
        if schema == u'config':
            use_config_path = os.path.join(
                os.path.dirname(os.path.abspath(self.config_file)), path)
            self._read_config_file(use_config_path)
            self._update_config()

    def get_config(self):
        return self.config.copy()


def error_shout(exception):
    click.secho(str(exception), fg=u'red', err=True)


def load_config(ini_path=None):
    if ini_path:
        if ini_path.startswith(u'~'):
            ini_path = os.path.expanduser(ini_path)
        filename = os.path.abspath(ini_path)
        config_source = u'-c parameter'
    elif os.environ.get(u'CKAN_INI'):
        filename = os.environ.get(u'CKAN_INI')
        config_source = u'$CKAN_INI'
    else:
        # deprecated method since CKAN 2.9
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

    config_loader = CKANConfigLoader(filename)
    loggingFileConfig(filename)
    log.info(u'Using configuration file {}'.format(filename))

    return config_loader.get_config()
