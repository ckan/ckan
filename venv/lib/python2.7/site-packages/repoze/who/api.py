from zope.interface import implementer

from repoze.who.interfaces import IAPI
from repoze.who.interfaces import IAPIFactory
from repoze.who.interfaces import IIdentifier
from repoze.who.interfaces import IAuthenticator
from repoze.who.interfaces import IChallenger
from repoze.who.interfaces import IMetadataProvider


def get_api(environ):
    return environ.get('repoze.who.api')


@implementer(IAPIFactory)
class APIFactory(object):

    def __init__(self,
                 identifiers=(),
                 authenticators=(),
                 challengers=(),
                 mdproviders=(),
                 request_classifier=None,
                 challenge_decider=None,
                 remote_user_key = 'REMOTE_USER',
                 logger=None,
                ):
        self.identifiers = identifiers
        self.authenticators = authenticators
        self.challengers = challengers
        self.mdproviders = mdproviders
        self.request_classifier = request_classifier
        self.challenge_decider = challenge_decider
        self.remote_user_key = remote_user_key
        self.logger = logger

    def __call__(self, environ):
        """ See IAPIFactory.
        """
        api = environ.get('repoze.who.api')
        if api is None:
            api = environ['repoze.who.api'] = API(environ, 
                                                  self.identifiers,
                                                  self.authenticators,
                                                  self.challengers,
                                                  self.mdproviders,
                                                  self.request_classifier,
                                                  self.challenge_decider,
                                                  self.remote_user_key,
                                                  self.logger,
                                                 )
        return api


def verify(plugin, iface):
    from zope.interface.verify import verifyObject
    verifyObject(iface, plugin, tentative=True)

 
def make_registries(identifiers, authenticators, challengers, mdproviders):
    from zope.interface.verify import BrokenImplementation
    interface_registry = {}
    name_registry = {}

    for supplied, iface in [ (identifiers, IIdentifier),
                             (authenticators, IAuthenticator),
                             (challengers, IChallenger),
                             (mdproviders, IMetadataProvider)]:

        for name, value in supplied:
            try:
                verify(value, iface)
            except BrokenImplementation as why:
                why = str(why)
                raise ValueError(str(name) + ': ' + why)
            L = interface_registry.setdefault(iface, [])
            L.append(value)
            name_registry[name] = value

    return interface_registry, name_registry


def match_classification(iface, plugins, classification):
    result = []
    for plugin in plugins:
        
        plugin_classifications = getattr(plugin, 'classifications', {})
        iface_classifications = plugin_classifications.get(iface)
        if not iface_classifications: # good for any
            result.append(plugin)
            continue
        if classification in iface_classifications:
            result.append(plugin)

    return result


@implementer(IAPI)
class API(object):

    def __init__(self,
                 environ,
                 identifiers,
                 authenticators,
                 challengers,
                 mdproviders,
                 request_classifier,
                 challenge_decider,
                 remote_user_key,
                 logger,
                ):
        self.environ = environ
        (self.interface_registry,
         self.name_registry) = make_registries(identifiers, authenticators,
                                               challengers, mdproviders)
        self.identifiers = identifiers
        self.authenticators = authenticators
        self.challengers = challengers
        self.mdproviders = mdproviders
        self.challenge_decider = challenge_decider
        self.remote_user_key = remote_user_key
        self.logger = logger
        classification = self.classification = (request_classifier and
                                                request_classifier(environ))
        logger and logger.info('request classification: %s' % classification)
        
    def authenticate(self):

        ids = self._identify()
            
        # ids will be list of tuples: [ (IIdentifier, identity) ]
        if ids:
            auth_ids = self._authenticate(ids)

            # auth_ids will be a list of five-tuples in the form
            #  ( (auth_rank, id_rank), authenticator, identifier, identity,
            #    userid )
            #
            # When sorted, its first element will represent the "best"
            # identity for this request.

            if auth_ids:
                auth_ids.sort()
                best = auth_ids[0]
                rank, authenticator, identifier, identity, userid = best
                identity = Identity(identity) # dont show contents at print
                identity['authenticator'] = authenticator
                identity['identifier'] = identifier

                # allow IMetadataProvider plugins to scribble on the identity
                self._add_metadata(identity)

                # add the identity to the environment; a downstream
                # application can mutate it to do an 'identity reset'
                # as necessary, e.g. identity['login'] = 'foo',
                # identity['password'] = 'bar'
                self.environ['repoze.who.identity'] = identity
                # set the REMOTE_USER
                self.environ[self.remote_user_key] = userid
                return identity

        self.logger and self.logger.info(
                        'no identities found, not authenticating')

    def challenge(self, status='403 Forbidden', app_headers=()):
        """ See IAPI.
        """
        identity = self.environ.get('repoze.who.identity', {})
        identifier = identity.get('identifier')

        logger = self.logger

        forget_headers = []

        if identifier:
            id_forget_headers = identifier.forget(self.environ, identity)
            if id_forget_headers is not None:
                forget_headers.extend(id_forget_headers)
                logger and logger.info('forgetting via headers from %s: %s'
                                       % (identifier, forget_headers))

        candidates = self.interface_registry.get(IChallenger, ())
        logger and logger.debug('challengers registered: %s' % repr(candidates))
        plugins = match_classification(IChallenger, candidates,
                                       self.classification)
        logger and logger.debug('challengers matched for '
                               'classification "%s": %s'
                                    % (self.classification, plugins))
        for plugin in plugins:
            app = plugin.challenge(self.environ, status, app_headers,
                                   forget_headers)
            if app is not None:
                # new WSGI application
                logger and logger.info(
                    'challenger plugin %s "challenge" returned an app' % (
                    plugin))
                return app

        # signifies no challenge
        logger and logger.info('no challenge app returned')
        return None

    def remember(self, identity=None):
        """ See IAPI.
        """
        headers = ()
        if identity is None:
            identity = self.environ.get('repoze.who.identity', {})
        identifier = identity.get('identifier')
        if identifier:
            got_headers = identifier.remember(self.environ, identity)
            if got_headers:
                headers = got_headers
                logger = self.logger
                logger and logger.info('remembering via headers from %s: %s'
                                        % (identifier, headers))
        return headers

    def forget(self, identity=None):
        """ See IAPI.
        """
        headers = ()
        if identity is None:
            identity = self.environ.get('repoze.who.identity', {})
        identifier = identity.get('identifier')
        if identifier:
            got_headers = identifier.forget(self.environ, identity)
            if got_headers:
                headers = got_headers
                logger = self.logger
                logger and logger.info('forgetting via headers from %s: %s'
                                        % (identifier, headers))
        return headers

    def login(self, credentials, identifier_name=None):
        """ See IAPI.
        """
        authenticated = identity = plugin = None
        headers = []

        # Filter identifiers using 'identifier_name', if provided.
        if identifier_name is not None:
            identifiers = [(name, plugin) for name, plugin in self.identifiers
                                           if name == identifier_name]
        else:
            identifiers = self.identifiers

        # First pass:  for each identifier, pretend that it was the source
        # of the credentials, and try to authenticate.
        for name, identifier in identifiers:
            authenticated = self._authenticate([(identifier, credentials)])

            if authenticated: # and therefore can remember it
                rank, plugin, identifier, identity, userid = authenticated[0]
                break

        # Second pass to allow identifiers which passed on auth to participate
        # in remember / forget.
        for name, identifier in identifiers:
            if identity is not None:
                i_headers = identifier.remember(self.environ, identity)
            else:
                i_headers = identifier.forget(self.environ, None)
            if i_headers is not None:
                headers.extend(i_headers)

        return identity, headers

    def logout(self, identifier_name=None):
        """ See IAPI.
        """
        authenticated = None
        headers = []
        # Filter identifiers using 'identifier_name', if provided.
        if identifier_name is not None:
            identifiers = [(name, plugin) for name, plugin in self.identifiers
                                           if name == identifier_name]
        else:
            identifiers = self.identifiers

        for name, identifier in identifiers:
            headers.extend(identifier.forget(self.environ, None))

        # we need to remove the identity for hybrid middleware/api usages to
        # work correctly: middleware calls ``remember`` unconditionally "on
        # the way out", and if an identity is found, competing login headers
        # will be set.
        if 'repoze.who.identity' in self.environ:
            del self.environ['repoze.who.identity']

        return headers

    def _identify(self):
        """ See IAPI.
        """
        logger = self.logger
        candidates = self.interface_registry.get(IIdentifier, ())
        logger and self.logger.debug('identifier plugins registered: %s' %
                                    (candidates,))
        plugins = match_classification(IIdentifier, candidates,
                                       self.classification)
        logger and self.logger.debug(
            'identifier plugins matched for '
            'classification "%s": %s' % (self.classification, plugins))

        results = []
        for plugin in plugins:
            identity = plugin.identify(self.environ)
            if identity is not None:
                logger and logger.debug(
                    'identity returned from %s: %s' % (plugin, identity))
                results.append((plugin, identity))
            else:
                logger and logger.debug(
                    'no identity returned from %s (%s)' % (plugin, identity))

        logger and logger.debug('identities found: %s' % (results,))
        return results

    def _authenticate(self, identities):
        """ See IAPI.
        """
        logger = self.logger
        candidates = self.interface_registry.get(IAuthenticator, [])
        logger and self.logger.debug('authenticator plugins registered: %s' %
                                    candidates)
        plugins = match_classification(IAuthenticator, candidates,
                                       self.classification)
        logger and self.logger.debug(
            'authenticator plugins matched for '
            'classification "%s": %s' % (self.classification, plugins))

        auth_rank = 0
        results = []

        for plugin in plugins:
            identifier_rank = 0
            for identifier, identity in identities:
                userid = plugin.authenticate(self.environ, identity)
                if userid is not None:
                    logger and logger.debug(
                        'userid returned from %s: "%s"' % (plugin, userid))

                    # stamp the identity with the userid
                    identity['repoze.who.userid'] = userid
                    rank = (auth_rank, identifier_rank)
                    results.append(
                        (rank, plugin, identifier, identity, userid)
                        )
                else:
                    logger and logger.debug(
                        'no userid returned from %s: (%s)' % (
                        plugin, userid))
                identifier_rank += 1
            auth_rank += 1

        logger and logger.debug('identities authenticated: %s' % (results,))
        return results

    def _add_metadata(self, identity):
        """ See IAPI.
        """
        candidates = self.interface_registry.get(IMetadataProvider, ())
        plugins = match_classification(IMetadataProvider, candidates,
                                       self.classification)        
        for plugin in plugins:
            plugin.add_metadata(self.environ, identity)

class Identity(dict):
    """ dict subclass: prevent members from being rendered during print
    """
    def __repr__(self):
        return '<repoze.who identity (hidden, dict-like) at %s>' % id(self)
    __str__ = __repr__
