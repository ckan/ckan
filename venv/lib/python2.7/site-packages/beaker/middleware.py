import warnings

try:
    from paste.registry import StackedObjectProxy
    beaker_session = StackedObjectProxy(name="Beaker Session")
    beaker_cache = StackedObjectProxy(name="Cache Manager")
except:
    beaker_cache = None
    beaker_session = None

from beaker.cache import CacheManager
from beaker.session import Session, SessionObject
from beaker.util import coerce_cache_params, coerce_session_params, \
    parse_cache_config_options


class CacheMiddleware(object):
    cache = beaker_cache

    def __init__(self, app, config=None, environ_key='beaker.cache', **kwargs):
        """Initialize the Cache Middleware

        The Cache middleware will make a CacheManager instance available
        every request under the ``environ['beaker.cache']`` key by
        default. The location in environ can be changed by setting
        ``environ_key``.

        ``config``
            dict  All settings should be prefixed by 'cache.'. This
            method of passing variables is intended for Paste and other
            setups that accumulate multiple component settings in a
            single dictionary. If config contains *no cache. prefixed
            args*, then *all* of the config options will be used to
            intialize the Cache objects.

        ``environ_key``
            Location where the Cache instance will keyed in the WSGI
            environ

        ``**kwargs``
            All keyword arguments are assumed to be cache settings and
            will override any settings found in ``config``

        """
        self.app = app
        config = config or {}

        self.options = {}

        # Update the options with the parsed config
        self.options.update(parse_cache_config_options(config))

        # Add any options from kwargs, but leave out the defaults this
        # time
        self.options.update(
            parse_cache_config_options(kwargs, include_defaults=False))

        # Assume all keys are intended for cache if none are prefixed with
        # 'cache.'
        if not self.options and config:
            self.options = config

        self.options.update(kwargs)
        self.cache_manager = CacheManager(**self.options)
        self.environ_key = environ_key

    def __call__(self, environ, start_response):
        if environ.get('paste.registry'):
            if environ['paste.registry'].reglist:
                environ['paste.registry'].register(self.cache,
                                                   self.cache_manager)
        environ[self.environ_key] = self.cache_manager
        return self.app(environ, start_response)


class SessionMiddleware(object):
    session = beaker_session

    def __init__(self, wrap_app, config=None, environ_key='beaker.session',
                 **kwargs):
        """Initialize the Session Middleware

        The Session middleware will make a lazy session instance
        available every request under the ``environ['beaker.session']``
        key by default. The location in environ can be changed by
        setting ``environ_key``.

        ``config``
            dict  All settings should be prefixed by 'session.'. This
            method of passing variables is intended for Paste and other
            setups that accumulate multiple component settings in a
            single dictionary. If config contains *no session. prefixed
            args*, then *all* of the config options will be used to
            intialize the Session objects.

        ``environ_key``
            Location where the Session instance will keyed in the WSGI
            environ

        ``**kwargs``
            All keyword arguments are assumed to be session settings and
            will override any settings found in ``config``

        """
        config = config or {}

        # Load up the default params
        self.options = dict(invalidate_corrupt=True, type=None,
                            data_dir=None, key='beaker.session.id',
                            timeout=None, save_accessed_time=True, secret=None,
                            log_file=None)

        # Pull out any config args meant for beaker session. if there are any
        for dct in [config, kwargs]:
            for key, val in dct.items():
                if key.startswith('beaker.session.'):
                    self.options[key[15:]] = val
                if key.startswith('session.'):
                    self.options[key[8:]] = val
                if key.startswith('session_'):
                    warnings.warn('Session options should start with session. '
                                  'instead of session_.', DeprecationWarning, 2)
                    self.options[key[8:]] = val

        # Coerce and validate session params
        coerce_session_params(self.options)

        # Assume all keys are intended for session if none are prefixed with
        # 'session.'
        if not self.options and config:
            self.options = config

        self.options.update(kwargs)
        self.wrap_app = self.app = wrap_app
        self.environ_key = environ_key

    def __call__(self, environ, start_response):
        session = SessionObject(environ, **self.options)
        if environ.get('paste.registry'):
            if environ['paste.registry'].reglist:
                environ['paste.registry'].register(self.session, session)
        environ[self.environ_key] = session
        environ['beaker.get_session'] = self._get_session

        if 'paste.testing_variables' in environ and 'webtest_varname' in self.options:
            environ['paste.testing_variables'][self.options['webtest_varname']] = session

        def session_start_response(status, headers, exc_info=None):
            if session.accessed():
                session.persist()
                if session.__dict__['_headers']['set_cookie']:
                    cookie = session.__dict__['_headers']['cookie_out']
                    if cookie:
                        headers.append(('Set-cookie', cookie))
            return start_response(status, headers, exc_info)
        return self.wrap_app(environ, session_start_response)

    def _get_session(self):
        return Session({}, use_cookies=False, **self.options)


def session_filter_factory(global_conf, **kwargs):
    def filter(app):
        return SessionMiddleware(app, global_conf, **kwargs)
    return filter


def session_filter_app_factory(app, global_conf, **kwargs):
    return SessionMiddleware(app, global_conf, **kwargs)
