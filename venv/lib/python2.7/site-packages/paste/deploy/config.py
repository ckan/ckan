# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""Paste Configuration Middleware and Objects"""
import threading
import re

# Loaded lazily
wsgilib = None
local = None

__all__ = ['DispatchingConfig', 'CONFIG', 'ConfigMiddleware', 'PrefixMiddleware']


def local_dict():
    global config_local, local
    try:
        return config_local.wsgi_dict
    except NameError:
        config_local = threading.local()
        config_local.wsgi_dict = result = {}
        return result
    except AttributeError:
        config_local.wsgi_dict = result = {}
        return result


class DispatchingConfig(object):

    """
    This is a configuration object that can be used globally,
    imported, have references held onto.  The configuration may differ
    by thread (or may not).

    Specific configurations are registered (and deregistered) either
    for the process or for threads.
    """

    # @@: What should happen when someone tries to add this
    # configuration to itself?  Probably the conf should become
    # resolved, and get rid of this delegation wrapper

    _constructor_lock = threading.Lock()

    def __init__(self):
        self._constructor_lock.acquire()
        try:
            self.dispatching_id = 0
            while 1:
                self._local_key = 'paste.processconfig_%i' % self.dispatching_id
                if not self._local_key in local_dict():
                    break
                self.dispatching_id += 1
        finally:
            self._constructor_lock.release()
        self._process_configs = []

    def push_thread_config(self, conf):
        """
        Make ``conf`` the active configuration for this thread.
        Thread-local configuration always overrides process-wide
        configuration.

        This should be used like::

            conf = make_conf()
            dispatching_config.push_thread_config(conf)
            try:
                ... do stuff ...
            finally:
                dispatching_config.pop_thread_config(conf)
        """
        local_dict().setdefault(self._local_key, []).append(conf)

    def pop_thread_config(self, conf=None):
        """
        Remove a thread-local configuration.  If ``conf`` is given,
        it is checked against the popped configuration and an error
        is emitted if they don't match.
        """
        self._pop_from(local_dict()[self._local_key], conf)

    def _pop_from(self, lst, conf):
        popped = lst.pop()
        if conf is not None and popped is not conf:
            raise AssertionError(
                "The config popped (%s) is not the same as the config "
                "expected (%s)"
                % (popped, conf))

    def push_process_config(self, conf):
        """
        Like push_thread_config, but applies the configuration to
        the entire process.
        """
        self._process_configs.append(conf)

    def pop_process_config(self, conf=None):
        self._pop_from(self._process_configs, conf)

    def __getattr__(self, attr):
        conf = self.current_conf()
        if conf is None:
            raise AttributeError(
                "No configuration has been registered for this process "
                "or thread")
        return getattr(conf, attr)

    def current_conf(self):
        thread_configs = local_dict().get(self._local_key)
        if thread_configs:
            return thread_configs[-1]
        elif self._process_configs:
            return self._process_configs[-1]
        else:
            return None

    def __getitem__(self, key):
        # I thought __getattr__ would catch this, but apparently not
        conf = self.current_conf()
        if conf is None:
            raise TypeError(
                "No configuration has been registered for this process "
                "or thread")
        return conf[key]

    def __contains__(self, key):
        # I thought __getattr__ would catch this, but apparently not
        return key in self

    def __setitem__(self, key, value):
        # I thought __getattr__ would catch this, but apparently not
        conf = self.current_conf()
        conf[key] = value

CONFIG = DispatchingConfig()


class ConfigMiddleware(object):

    """
    A WSGI middleware that adds a ``paste.config`` key to the request
    environment, as well as registering the configuration temporarily
    (for the length of the request) with ``paste.CONFIG``.
    """

    def __init__(self, application, config):
        """
        This delegates all requests to `application`, adding a *copy*
        of the configuration `config`.
        """
        self.application = application
        self.config = config

    def __call__(self, environ, start_response):
        global wsgilib
        if wsgilib is None:
            import pkg_resources
            pkg_resources.require('Paste')
            from paste import wsgilib
        popped_config = None
        if 'paste.config' in environ:
            popped_config = environ['paste.config']
        conf = environ['paste.config'] = self.config.copy()
        app_iter = None
        CONFIG.push_thread_config(conf)
        try:
            app_iter = self.application(environ, start_response)
        finally:
            if app_iter is None:
                # An error occurred...
                CONFIG.pop_thread_config(conf)
                if popped_config is not None:
                    environ['paste.config'] = popped_config
        if type(app_iter) in (list, tuple):
            # Because it is a concrete iterator (not a generator) we
            # know the configuration for this thread is no longer
            # needed:
            CONFIG.pop_thread_config(conf)
            if popped_config is not None:
                environ['paste.config'] = popped_config
            return app_iter
        else:
            def close_config():
                CONFIG.pop_thread_config(conf)
            new_app_iter = wsgilib.add_close(app_iter, close_config)
            return new_app_iter


def make_config_filter(app, global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)
    return ConfigMiddleware(app, conf)

make_config_middleware = ConfigMiddleware.__doc__


class PrefixMiddleware(object):
    """Translate a given prefix into a SCRIPT_NAME for the filtered
    application.

    PrefixMiddleware provides a way to manually override the root prefix
    (SCRIPT_NAME) of your application for certain, rare situations.

    When running an application under a prefix (such as '/james') in
    FastCGI/apache, the SCRIPT_NAME environment variable is automatically
    set to to the appropriate value: '/james'. Pylons' URL generating
    functions, such as url_for, always take the SCRIPT_NAME value into account.

    One situation where PrefixMiddleware is required is when an application
    is accessed via a reverse proxy with a prefix. The application is accessed
    through the reverse proxy via the the URL prefix '/james', whereas the
    reverse proxy forwards those requests to the application at the prefix '/'.

    The reverse proxy, being an entirely separate web server, has no way of
    specifying the SCRIPT_NAME variable; it must be manually set by a
    PrefixMiddleware instance. Without setting SCRIPT_NAME, url_for will
    generate URLs such as: '/purchase_orders/1', when it should be
    generating: '/james/purchase_orders/1'.

    To filter your application through a PrefixMiddleware instance, add the
    following to the '[app:main]' section of your .ini file:

    .. code-block:: ini

        filter-with = proxy-prefix

        [filter:proxy-prefix]
        use = egg:PasteDeploy#prefix
        prefix = /james

    The name ``proxy-prefix`` simply acts as an identifier of the filter
    section; feel free to rename it.

    Also, unless disabled, the ``X-Forwarded-Server`` header will be
    translated to the ``Host`` header, for cases when that header is
    lost in the proxying.  Also ``X-Forwarded-Host``,
    ``X-Forwarded-Scheme``, and ``X-Forwarded-Proto`` are translated.

    If ``force_port`` is set, SERVER_PORT and HTTP_HOST will be
    rewritten with the given port.  You can use a number, string (like
    '80') or the empty string (whatever is the default port for the
    scheme).  This is useful in situations where there is port
    forwarding going on, and the server believes itself to be on a
    different port than what the outside world sees.

    You can also use ``scheme`` to explicitly set the scheme (like
    ``scheme = https``).
    """
    def __init__(self, app, global_conf=None, prefix='/',
                 translate_forwarded_server=True,
                 force_port=None, scheme=None):
        self.app = app
        self.prefix = prefix.rstrip('/')
        self.translate_forwarded_server = translate_forwarded_server
        self.regprefix = re.compile("^%s(.*)$" % self.prefix)
        self.force_port = force_port
        self.scheme = scheme

    def __call__(self, environ, start_response):
        url = environ['PATH_INFO']
        url = re.sub(self.regprefix, r'\1', url)
        if not url:
            url = '/'
        environ['PATH_INFO'] = url
        environ['SCRIPT_NAME'] = self.prefix
        if self.translate_forwarded_server:
            if 'HTTP_X_FORWARDED_SERVER' in environ:
                environ['SERVER_NAME'] = environ['HTTP_HOST'] = environ.pop('HTTP_X_FORWARDED_SERVER').split(',')[0]
            if 'HTTP_X_FORWARDED_HOST' in environ:
                environ['HTTP_HOST'] = environ.pop('HTTP_X_FORWARDED_HOST').split(',')[0]
            if 'HTTP_X_FORWARDED_FOR' in environ:
                environ['REMOTE_ADDR'] = environ.pop('HTTP_X_FORWARDED_FOR').split(',')[0]
            if 'HTTP_X_FORWARDED_SCHEME' in environ:
                environ['wsgi.url_scheme'] = environ.pop('HTTP_X_FORWARDED_SCHEME')
            elif 'HTTP_X_FORWARDED_PROTO' in environ:
                environ['wsgi.url_scheme'] = environ.pop('HTTP_X_FORWARDED_PROTO')
        if self.force_port is not None:
            host = environ.get('HTTP_HOST', '').split(':', 1)[0]
            if self.force_port:
                host = '%s:%s' % (host, self.force_port)
                environ['SERVER_PORT'] = str(self.force_port)
            else:
                if environ['wsgi.url_scheme'] == 'http':
                    port = '80'
                else:
                    port = '443'
                environ['SERVER_PORT'] = port
            environ['HTTP_HOST'] = host
        if self.scheme is not None:
            environ['wsgi.url_scheme'] = self.scheme
        return self.app(environ, start_response)


def make_prefix_middleware(
    app, global_conf, prefix='/',
    translate_forwarded_server=True,
    force_port=None, scheme=None):
    from paste.deploy.converters import asbool
    translate_forwarded_server = asbool(translate_forwarded_server)
    return PrefixMiddleware(
        app, prefix=prefix,
        translate_forwarded_server=translate_forwarded_server,
        force_port=force_port, scheme=scheme)

make_prefix_middleware.__doc__ = PrefixMiddleware.__doc__
