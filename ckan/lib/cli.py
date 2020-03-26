# encoding: utf-8

from __future__ import print_function

import os
import sys

import click
import paste.script
import routes
from paste.registry import Registry
from paste.script.util.logging_config import fileConfig
from six.moves import input
from six.moves.urllib.parse import urlparse

from ckan.config.middleware import make_app
from ckan.cli import load_config as _get_config
import ckan.logic as logic
import ckan.model as model
from ckan.common import config
from ckan.common import asbool
import ckan.lib.maintain as maintain
# This is a test Flask request context to be used internally.
# Do not use it!
_cli_test_request_context = None


# NB No CKAN imports are allowed until after the config file is loaded.
#    i.e. do the imports in methods, after _load_config is called.
#    Otherwise loggers get disabled.


@maintain.deprecated('Use @maintain.deprecated instead')
def deprecation_warning(message=None):
    '''
    DEPRECATED

    Print a deprecation warning to STDERR.

    If ``message`` is given it is also printed to STDERR.
    '''
    sys.stderr.write(u'WARNING: This function is deprecated.')
    if message:
        sys.stderr.write(u' ' + message.strip())
    sys.stderr.write(u'\n')


@maintain.deprecated()
def error(msg):
    '''
    DEPRECATED

    Print an error message to STDOUT and exit with return code 1.
    '''
    sys.stderr.write(msg)
    if not msg.endswith('\n'):
        sys.stderr.write('\n')
    sys.exit(1)


@maintain.deprecated('Use model.parse_db_config directly instead')
def _parse_db_config(config_key=u'sqlalchemy.url'):
    '''Deprecated'''
    db_config = model.parse_db_config(config_key)
    if not db_config:
        raise Exception(
            u'Could not extract db details from url: %r' % config[config_key]
        )
    return db_config

## from http://code.activestate.com/recipes/577058/ MIT licence.
## Written by Trent Mick
@maintain.deprecated('Instead you can probably use click.confirm()')
def query_yes_no(question, default="yes"):
    """DEPRECATED

    Ask a yes/no question via input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes": "yes",   "y": "yes",  "ye": "yes",
             "no": "no",     "n": "no"}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while 1:
        sys.stdout.write(question + prompt)
        choice = input().strip().lower()
        if default is not None and choice == '':
            return default
        elif choice in valid.keys():
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


class MockTranslator(object):
    def gettext(self, value):
        return value

    def ugettext(self, value):
        return value

    def ungettext(self, singular, plural, n):
        if n > 1:
            return plural
        return singular


def load_config(config, load_site_user=True):
    conf = _get_config(config)
    assert 'ckan' not in dir()  # otherwise loggers would be disabled
    # We have now loaded the config. Now we can import ckan for the
    # first time.
    from ckan.config.environment import load_environment
    load_environment(conf)

    # Set this internal test request context with the configured environment so
    # it can be used when calling url_for from the CLI.
    global _cli_test_request_context

    app = make_app(conf)
    flask_app = app.apps['flask_app']._wsgi_app
    _cli_test_request_context = flask_app.test_request_context()

    registry = Registry()
    registry.prepare()
    import pylons
    registry.register(pylons.translator, MockTranslator())

    site_user = None
    if model.user_table.exists() and load_site_user:
        # If the DB has already been initialized, create and register
        # a pylons context object, and add the site user to it, so the
        # auth works as in a normal web request
        c = pylons.util.AttribSafeContextObj()

        registry.register(pylons.c, c)

        site_user = logic.get_action('get_site_user')({'ignore_auth': True}, {})

        pylons.c.user = site_user['name']
        pylons.c.userobj = model.User.get(site_user['name'])

    ## give routes enough information to run url_for
    parsed = urlparse(conf.get('ckan.site_url', 'http://0.0.0.0'))
    request_config = routes.request_config()
    request_config.host = parsed.netloc + parsed.path
    request_config.protocol = parsed.scheme

    return site_user


@maintain.deprecated('Instead use ckan.cli.cli.CkanCommand or extensions '
                     'should use IClick')
def paster_click_group(summary):
    '''DEPRECATED

    Return a paster command click.Group for paster subcommands

    :param command: the paster command linked to this function from
        setup.py, used in help text (e.g. "datastore")
    :param summary: summary text used in paster's help/command listings
        (e.g. "Perform commands to set up the datastore")
    '''
    class PasterClickGroup(click.Group):
        '''A click.Group that may be called like a paster command'''
        def __call__(self, ignored_command):
            sys.argv.remove(ignored_command)
            return super(PasterClickGroup, self).__call__(
                prog_name=u'paster ' + ignored_command,
                help_option_names=[u'-h', u'--help'],
                obj={})

    @click.group(cls=PasterClickGroup)
    @click.option(
        '--plugin',
        metavar='ckan',
        help='paster plugin (when run outside ckan directory)')
    @click_config_option
    @click.pass_context
    def cli(ctx, plugin, config):
        ctx.obj['config'] = config


    cli.summary = summary
    cli.group_name = u'ckan'
    return cli


# common definition for paster ... --config
click_config_option = click.option(
    '-c',
    '--config',
    default=None,
    metavar='CONFIG',
    help=u'Config file to use (default: development.ini)')


class CkanCommand(paste.script.command.Command):
    '''DEPRECATED - Instead use ckan.cli.cli.CkanCommand or extensions
    should use IClick.

    Base class for classes that implement CKAN paster commands to
    inherit.'''
    parser = paste.script.command.Command.standard_parser(verbose=True)
    parser.add_option('-c', '--config', dest='config',
                      help='Config file to use.')
    parser.add_option('-f', '--file',
                      action='store',
                      dest='file_path',
                      help="File to dump results to (if needed)")
    default_verbosity = 1
    group_name = 'ckan'

    def _load_config(self, load_site_user=True):
        self.site_user = load_config(self.options.config, load_site_user)
