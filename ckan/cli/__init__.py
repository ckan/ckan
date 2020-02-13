# encoding: utf-8

import os

import click
import logging
from configparser import ConfigParser


log = logging.getLogger(__name__)


class CKANConfigLoader(object):
    def __init__(self, filename):
        self.filename = filename = filename.strip()
        self.parser = ConfigParser()
        self.section = u'app:main'
        self.read_config_files(filename)

        defaults = {
            u'here': os.path.dirname(os.path.abspath(filename)),
            u'__file__': os.path.abspath(filename)
        }
        self._update_defaults(defaults)

    def read_config_files(self, filename):
        '''Read and parses a config file.

        If the config file has 'use=config:<filename>' then it parses both
        files. Automatically applies interpolation if needed.
        '''
        self.parser.read(filename)

        schema, path = self.parser.get(self.section, u'use').split(u':')
        if schema == u'config':
            path = os.path.join(
                os.path.dirname(os.path.abspath(filename)), path)
            self.parser.read([path, filename])

    def _update_defaults(self, new_defaults):
        for key, value in new_defaults.items():
            self.parser._defaults[key] = value

    def get_config(self):
        '''Returns a dictionary with all the configurations.

        The dictionay will include configs from DEFAULT and app:main sections.
        If two files were parsed the configs of the second file one will
        override all the values of the first file regardless the section.
        '''
        config = {}
        # The global_config key is to keep compatibility with Pylons. It can be
        # safely removed when the Flask migration is completed.
        config['global_conf'] = self.parser.defaults().copy()

        options = self.parser.options(self.section)
        for option in options:
            value = self.parser.get(self.section, option)
            config[option] = value
            if option in config['global_conf']:
                config['global_conf'][option] = value

        return config


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
    log.info(u'Using configuration file {}'.format(filename))

    return config_loader.get_config()
