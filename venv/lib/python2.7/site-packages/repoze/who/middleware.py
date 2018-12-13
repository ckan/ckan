import logging
import sys

from repoze.who.api import APIFactory
from repoze.who.interfaces import IChallenger
from repoze.who._compat import StringIO

_STARTED = '-- repoze.who request started (%s) --'
_ENDED = '-- repoze.who request ended (%s) --'

class PluggableAuthenticationMiddleware(object):
    def __init__(self,
                 app,
                 identifiers,
                 authenticators,
                 challengers,
                 mdproviders,
                 request_classifier = None,
                 challenge_decider = None,
                 log_stream = None,
                 log_level = logging.INFO,
                 remote_user_key = 'REMOTE_USER',
                 classifier = None
                 ):
        if challenge_decider is None:
            raise ValueError('challenge_decider is required')
        if request_classifier is not None and classifier is not None:
            raise ValueError(
                    'Only one of request_classifier and classifier is allowed')
        if request_classifier is None:
            if classifier is None:
                raise ValueError(
                        'Either request_classifier or classifier is required')
            request_classifier = classifier
        self.app = app
        logger = self.logger = None
        if isinstance(log_stream, logging.Logger):
            logger = self.logger = log_stream
        elif log_stream:
            handler = logging.StreamHandler(log_stream)
            fmt = '%(asctime)s %(message)s'
            formatter = logging.Formatter(fmt)
            handler.setFormatter(formatter)
            logger = self.logger = logging.Logger('repoze.who')
            logger.addHandler(handler)
            logger.setLevel(log_level)
        self.remote_user_key = remote_user_key

        self.api_factory = APIFactory(identifiers,
                                      authenticators,
                                      challengers, 
                                      mdproviders,
                                      request_classifier,
                                      challenge_decider,
                                      remote_user_key,
                                      logger
                                     )


    def __call__(self, environ, start_response):
        if self.remote_user_key in environ:
            # act as a pass through if REMOTE_USER (or whatever) is
            # already set
            return self.app(environ, start_response)

        api = self.api_factory(environ)

        environ['repoze.who.plugins'] = api.name_registry # BBB?
        environ['repoze.who.logger'] = self.logger
        environ['repoze.who.application'] = self.app

        logger = self.logger
        path_info = environ.get('PATH_INFO', None)
        logger and logger.info(_STARTED % path_info)
        api.authenticate()  # identity saved in environ

        # allow identifier plugins to replace the downstream
        # application (to do redirection and unauthorized themselves
        # mostly)
        app = environ.pop('repoze.who.application')
        if  app is not self.app:
            logger and logger.info(
                'static downstream application replaced with %s' % app)

        wrapper = StartResponseWrapper(start_response)
        app_iter = app(environ, wrapper.wrap_start_response)

        # The challenge decider almost(?) always needs information from the
        # response.  The WSGI spec (PEP 333) states that a WSGI application
        # must call start_response by the iterable's first iteration.  If
        # start_response hasn't been called, we'll wrap it in a way that
        # triggers that call.
        if not wrapper.called:
            app_iter = wrap_generator(app_iter)

        if api.challenge_decider(environ, wrapper.status, wrapper.headers):
            logger and logger.info('challenge required')
            close = getattr(app_iter, 'close', _no_op)

            challenge_app = api.challenge(wrapper.status, wrapper.headers)
            if challenge_app is not None:
                logger and logger.info('executing challenge app')
                if app_iter:
                    list(app_iter) # unwind the original app iterator
                # PEP 333 requires that we call the original iterator's
                # 'close' method, if it exists, before releasing it.
                close()
                # replace the downstream app with the challenge app
                app_iter = challenge_app(environ, start_response)
            else:
                logger and logger.info('configuration error: no challengers')
                close()
                raise RuntimeError('no challengers found')
        else:
            logger and logger.info('no challenge required')
            remember_headers = api.remember()
            wrapper.finish_response(remember_headers)

        logger and logger.info(_ENDED % path_info)
        return app_iter

def _no_op():
    pass

def wrap_generator(result):
    """\
    This function returns a generator that behaves exactly the same as the
    original.  It's only difference is it pulls the first iteration off and
    caches it to trigger any immediate side effects (in a WSGI world, this
    ensures start_response is called).
    """
    # PEP 333 requires that we call the original iterator's
    # 'close' method, if it exists, before releasing it.
    close = getattr(result, 'close', lambda: None)
    # Neat trick to pull the first iteration only. We need to do this outside
    # of the generator function to ensure it is called.
    first = marker = []
    for iter in result:
        first = iter
        break

    # Wrapper yields the first iteration, then passes result's iterations
    # directly up.
    def wrapper():
        if first is not marker:
            yield first
        for iter in result:
            # We'll let result's StopIteration bubble up directly.
            yield iter
        close()
    return wrapper()

class StartResponseWrapper(object):
    def __init__(self, start_response):
        self.start_response = start_response
        self.status = None
        self.headers = []
        self.exc_info = None
        self.buffer = StringIO()
        # A WSGI app may delay calling start_response until the first iteration
        # of its generator.  We track this so we know whether or not we need to
        # trigger an iteration before examining the response.
        self.called = False

    def wrap_start_response(self, status, headers, exc_info=None):
        self.headers = headers
        self.status = status
        self.exc_info = exc_info
        # The response has been initiated, so we have a valid code.
        self.called = True
        return self.buffer.write

    def finish_response(self, extra_headers):
        if not extra_headers:
            extra_headers = []
        headers = self.headers + extra_headers
        write = self.start_response(self.status, headers, self.exc_info)
        if write:
            self.buffer.seek(0)
            value = self.buffer.getvalue()
            if value:
                write(value)
            if hasattr(write, 'close'):
                write.close()

def make_test_middleware(app, global_conf):
    """ Functionally equivalent to

    [plugin:redirector]
    use = repoze.who.plugins.redirector.RedirectorPlugin
    login_url = /login.html

    [plugin:auth_tkt]
    use = repoze.who.plugins.auth_tkt:AuthTktCookiePlugin
    secret = SEEKRIT
    cookie_name = oatmeal

    [plugin:basicauth]
    use = repoze.who.plugins.basicauth.BasicAuthPlugin
    realm = repoze.who

    [plugin:htpasswd]
    use = repoze.who.plugins.htpasswd.HTPasswdPlugin
    filename = <...>
    check_fn = repoze.who.plugins.htpasswd:crypt_check

    [general]
    request_classifier = repoze.who.classifiers:default_request_classifier
    challenge_decider = repoze.who.classifiers:default_challenge_decider

    [identifiers]
    plugins = authtkt basicauth

    [authenticators]
    plugins = authtkt htpasswd

    [challengers]
    plugins = redirector:browser basicauth
    """
    # be able to test without a config file
    from repoze.who.plugins.basicauth import BasicAuthPlugin
    from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin
    from repoze.who.plugins.redirector import RedirectorPlugin
    from repoze.who.plugins.htpasswd import HTPasswdPlugin
    io = StringIO()
    for name, password in [ ('admin', 'admin'), ('chris', 'chris') ]:
        io.write('%s:%s\n' % (name, password))
    io.seek(0)
    def cleartext_check(password, hashed):
        return password == hashed #pragma NO COVERAGE
    htpasswd = HTPasswdPlugin(io, cleartext_check)
    basicauth = BasicAuthPlugin('repoze.who')
    auth_tkt = AuthTktCookiePlugin('secret', 'auth_tkt')
    redirector = RedirectorPlugin('/login.html')
    redirector.classifications = {IChallenger: ['browser']} # only for browser
    identifiers = [('auth_tkt', auth_tkt),
                   ('basicauth', basicauth),
                  ]
    authenticators = [('htpasswd', htpasswd)]
    challengers = [('redirector', redirector),
                   ('basicauth', basicauth)]
    mdproviders = []
    from repoze.who.classifiers import default_request_classifier
    from repoze.who.classifiers import default_challenge_decider
    log_stream = None
    import os
    if os.environ.get('WHO_LOG'):
        log_stream = sys.stdout
    middleware = PluggableAuthenticationMiddleware(
        app,
        identifiers,
        authenticators,
        challengers,
        mdproviders,
        default_request_classifier,
        default_challenge_decider,
        log_stream = log_stream,
        log_level = logging.DEBUG
        )
    return middleware
