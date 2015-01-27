import os
import sys
import re
import ckan.logic as logic
import ckan.model as model
import urlparse
import routes

import paste.script
from paste.registry import Registry
from paste.script.util.logging_config import fileConfig

# NB No CKAN imports are allowed until after the config file is loaded.
#   i.e. do the imports in methods, after _load_config is called.
#   Otherwise loggers get disabled.


def parse_db_config(config_key='sqlalchemy.url'):
    ''' Takes a config key for a database connection url and parses it into
    a dictionary. Expects a url like:

    'postgres://tester:pass@localhost/ckantest3'
    '''
    from pylons import config
    url = config[config_key]
    regex = [
        '^\s*(?P<db_type>\w*)',
        '://',
        '(?P<db_user>[^:]*)',
        ':?',
        '(?P<db_pass>[^@]*)',
        '@',
        '(?P<db_host>[^/:]*)',
        ':?',
        '(?P<db_port>[^/]*)',
        '/',
        '(?P<db_name>[\w.-]*)'
    ]
    db_details_match = re.match(''.join(regex), url)
    if not db_details_match:
        raise Exception('Could not extract db details from url: %r' % url)
    db_details = db_details_match.groupdict()
    return db_details


# from http://code.activestate.com/recipes/577058/ MIT licence.
# Written by Trent Mick
def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes": "yes", "y": "yes", "ye": "yes",
             "no": "no", "n": "no"}
    if not default:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while 1:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
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


class CkanCommand(paste.script.command.Command):
    '''Base class for classes that implement CKAN paster commands to inherit.

    '''
    parser = paste.script.command.Command.standard_parser(verbose=True)
    parser.add_option('-c', '--config', dest='config',
                      help='Config file to use.')
    parser.add_option('-f', '--file',
                      action='store',
                      dest='file_path',
                      help="File to dump results to (if needed)")
    default_verbosity = 1
    group_name = 'ckan'

    def _get_config(self):
        from paste.deploy import appconfig

        if self.options.config:
            self.filename = os.path.abspath(self.options.config)
            config_source = '-c parameter'
        elif os.environ.get('CKAN_INI'):
            self.filename = os.environ.get('CKAN_INI')
            config_source = '$CKAN_INI'
        else:
            self.filename = os.path.join(os.getcwd(), 'development.ini')
            config_source = 'default value'

        if not os.path.exists(self.filename):
            msg = 'Config file not found: %s' % self.filename
            msg += '\n(Given by: %s)' % config_source
            raise self.BadCommand(msg)

        fileConfig(self.filename)
        return appconfig('config:' + self.filename)

    def _load_config(self, load_site_user=True):
        conf = self._get_config()
        assert 'ckan' not in dir()  # otherwise loggers would be disabled

        # We have now loaded the config. Now we can import ckan for the
        # first time.
        from ckan.config.environment import load_environment
        load_environment(conf.global_conf, conf.local_conf)

        self.registry = Registry()
        self.registry.prepare()

        import pylons
        self.translator_obj = MockTranslator()
        self.registry.register(pylons.translator, self.translator_obj)

        if model.user_table.exists() and load_site_user:
            # If the DB has already been initialized, create and register
            # a pylons context object, and add the site user to it, so the
            # auth works as in a normal web request
            c = pylons.util.AttribSafeContextObj()

            self.registry.register(pylons.c, c)

            self.site_user = logic.get_action('get_site_user')(
                {'ignore_auth': True}, {})

            pylons.c.user = self.site_user['name']
            pylons.c.userobj = model.User.get(self.site_user['name'])

        # give routes enough information to run url_for
        parsed = urlparse.urlparse(conf.get('ckan.site_url', 'http://0.0.0.0'))
        request_config = routes.request_config()
        request_config.host = parsed.netloc + parsed.path
        request_config.protocol = parsed.scheme

    def _setup_app(self):
        cmd = paste.script.appinstall.SetupCommand('setup-app')
        cmd.run([self.filename])
