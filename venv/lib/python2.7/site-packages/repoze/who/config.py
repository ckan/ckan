""" Configuration parser
"""
import logging
from pkg_resources import EntryPoint
import sys
import warnings

from repoze.who.api import APIFactory
from repoze.who.interfaces import IAuthenticator
from repoze.who.interfaces import IChallengeDecider
from repoze.who.interfaces import IChallenger
from repoze.who.interfaces import IIdentifier
from repoze.who.interfaces import IMetadataProvider
from repoze.who.interfaces import IPlugin
from repoze.who.interfaces import IRequestClassifier
from repoze.who.middleware import PluggableAuthenticationMiddleware
from repoze.who._compat import StringIO
from repoze.who._compat import ConfigParser
from repoze.who._compat import ParsingError

def _resolve(name):
    if name:
        return EntryPoint.parse('x=%s' % name).resolve()

class WhoConfig:
    def __init__(self, here):
        self.here = here
        self.request_classifier = None
        self.challenge_decider = None
        self.plugins = {}
        self.identifiers = []
        self.authenticators = []
        self.challengers = []
        self.mdproviders = []
        self.remote_user_key = 'REMOTE_USER'

    def _makePlugin(self, name, iface, options=None):
        if options is None:
            options = {}
        obj = _resolve(name)
        if not iface.providedBy(obj):
            obj = obj(**options)
        return obj

    def _getPlugin(self, name, iface):
        obj = self.plugins.get(name)
        if obj is None:
            obj = self._makePlugin(name, iface)
        return obj

    def _parsePluginSequence(self, attr, proptext, iface):
        lines = proptext.split()
        for line in lines:

            if ';' in line:
                plugin_name, classifier = line.split(';')
            else:
                plugin_name = line
                classifier = None

            plugin = self._getPlugin(plugin_name, iface)

            if classifier is not None:
                classifications = getattr(plugin, 'classifications', None)
                if classifications is None:
                    classifications = plugin.classifications = {}
                classifications[iface] = classifier

            attr.append((plugin_name, plugin))

    def parse(self, text):
        if getattr(text, 'readline', None) is None:
            text = StringIO(text)
        cp = ConfigParser(defaults={'here': self.here})
        try:
            cp.read_file(text)
        except AttributeError: #pragma NO COVER Python < 3.0
            cp.readfp(text)

        for s_id in [x for x in cp.sections() if x.startswith('plugin:')]:
            plugin_id = s_id[len('plugin:'):]
            options = dict(cp.items(s_id))
            if 'use' in options:
                name = options.pop('use')
                del options['here']
                obj = self._makePlugin(name, IPlugin, options)
                self.plugins[plugin_id] = obj

        if 'general' in cp.sections():
            general = dict(cp.items('general'))

            rc = general.get('request_classifier')
            if rc is not None:
                rc = self._getPlugin(rc, IRequestClassifier)
            self.request_classifier = rc

            cd = general.get('challenge_decider')
            if cd is not None:
                cd = self._getPlugin(cd, IChallengeDecider)
            self.challenge_decider = cd

            ru = general.get('remote_user_key')
            if ru is not None:
                self.remote_user_key = ru

        if 'identifiers' in cp.sections():
            identifiers = dict(cp.items('identifiers'))
            self._parsePluginSequence(self.identifiers,
                                      identifiers['plugins'],
                                      IIdentifier,
                                     )

        if 'authenticators' in cp.sections():
            authenticators = dict(cp.items('authenticators'))
            self._parsePluginSequence(self.authenticators,
                                      authenticators['plugins'],
                                      IAuthenticator,
                                     )

        if 'challengers' in cp.sections():
            challengers = dict(cp.items('challengers'))
            self._parsePluginSequence(self.challengers,
                                      challengers['plugins'],
                                      IChallenger,
                                     )

        if 'mdproviders' in cp.sections():
            mdproviders = dict(cp.items('mdproviders'))
            self._parsePluginSequence(self.mdproviders,
                                      mdproviders['plugins'],
                                      IMetadataProvider,
                                     )


class NullHandler(logging.Handler):
    def emit(self, record):
        pass


_LEVELS = {'debug': logging.DEBUG,
           'info': logging.INFO,
           'warning': logging.WARNING,
           'error': logging.ERROR,
          }

def make_api_factory_with_config(global_conf,
                                 config_file,
                                 remote_user_key = 'REMOTE_USER',
                                 logger=None,
                                ):
    identifiers = authenticators = challengers = mdproviders = ()
    request_classifier = None
    challenge_decider = None
    parser = WhoConfig(global_conf['here'])
    try:
        opened = open(config_file)
    except IOError:
        warnings.warn('Non-existent who config file: %s' % config_file,
                      stacklevel=2)
    else:
        try:
            try:
                parser.parse(opened)
            except ParsingError:
                warnings.warn('Invalid who config file: %s' % config_file,
                            stacklevel=2)
            else:
                identifiers = parser.identifiers
                authenticators = parser.authenticators
                challengers = parser.challengers
                mdproviders = parser.mdproviders
                request_classifier = parser.request_classifier
                challenge_decider = parser.challenge_decider
        finally:
            opened.close()

    return APIFactory(identifiers,
                      authenticators,
                      challengers,
                      mdproviders,
                      request_classifier,
                      challenge_decider,
                      remote_user_key,
                      logger,
                     )

def make_middleware_with_config(app, global_conf, config_file,
                                log_file=None, log_level=None):
    parser = WhoConfig(global_conf['here'])
    with open(config_file) as f:
        parser.parse(f)
    log_stream = None

    if log_level is None:
        log_level = logging.INFO
    elif not isinstance(log_level, int):
        log_level = _LEVELS[log_level.lower()]

    if log_file is not None:
        if log_file.lower() == 'stdout':
            log_stream = sys.stdout
        else:
            log_stream = open(log_file, 'wb')
    else:
        log_stream = logging.getLogger('repoze.who')
        log_stream.addHandler(NullHandler())
        log_stream.setLevel(log_level or 0)

    return PluggableAuthenticationMiddleware(
                app,
                parser.identifiers,
                parser.authenticators,
                parser.challengers,
                parser.mdproviders,
                parser.request_classifier,
                parser.challenge_decider,
                log_stream,
                log_level,
                parser.remote_user_key,
           )
