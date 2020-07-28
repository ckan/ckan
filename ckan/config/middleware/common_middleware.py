# encoding: utf-8

"""Common middleware used by both Flask and Pylons app stacks."""

import urllib2
import hashlib
import urllib
import json
from urlparse import urlparse

import sqlalchemy as sa

from ckan.common import config

from ckan.lib.i18n import get_locales_from_config


class I18nMiddleware(object):
    """I18n Middleware selects the language based on the url
    eg /fr/home is French"""
    def __init__(self, app, config):
        self.app = app
        self.default_locale = config.get('ckan.locale_default', 'en')
        self.local_list = get_locales_from_config()

    def __call__(self, environ, start_response):
        # strip the language selector from the requested url
        # and set environ variables for the language selected
        # CKAN_LANG is the language code eg en, fr
        # CKAN_LANG_IS_DEFAULT is set to True or False
        # CKAN_CURRENT_URL is set to the current application url

        # We only update once for a request so we can keep
        # the language and original url which helps with 404 pages etc
        if 'CKAN_LANG' not in environ:
            path_parts = environ['PATH_INFO'].split('/')
            if len(path_parts) > 1 and path_parts[1] in self.local_list:
                environ['CKAN_LANG'] = path_parts[1]
                environ['CKAN_LANG_IS_DEFAULT'] = False
                # rewrite url
                if len(path_parts) > 2:
                    environ['PATH_INFO'] = '/'.join([''] + path_parts[2:])
                else:
                    environ['PATH_INFO'] = '/'
            else:
                environ['CKAN_LANG'] = self.default_locale
                environ['CKAN_LANG_IS_DEFAULT'] = True

            # Current application url
            path_info = environ['PATH_INFO']
            # sort out weird encodings
            path_info = \
                '/'.join(urllib.quote(pce, '') for pce in path_info.split('/'))

            qs = environ.get('QUERY_STRING')

            if qs:
                # sort out weird encodings
                qs = urllib.quote(qs, '')
                environ['CKAN_CURRENT_URL'] = '%s?%s' % (path_info, qs)
            else:
                environ['CKAN_CURRENT_URL'] = path_info

        return self.app(environ, start_response)


class RootPathMiddleware(object):
    '''
    Prevents the SCRIPT_NAME server variable conflicting with the ckan.root_url
    config. The routes package uses the SCRIPT_NAME variable and appends to the
    path and ckan addes the root url causing a duplication of the root path.

    This is a middleware to ensure that even redirects use this logic.
    '''
    def __init__(self, app, config):
        self.app = app

    def __call__(self, environ, start_response):
        # Prevents the variable interfering with the root_path logic
        if 'SCRIPT_NAME' in environ:
            environ['SCRIPT_NAME'] = ''

        return self.app(environ, start_response)


class PageCacheMiddleware(object):
    ''' A simple page cache that can store and serve pages. It uses
    Redis as storage. It caches pages that have a http status code of
    200, use the GET method. Only non-logged in users receive cached
    pages.
    Cachable pages are indicated by a environ CKAN_PAGE_CACHABLE
    variable.'''

    def __init__(self, app, config):
        self.app = app
        import redis    # only import if used
        self.redis = redis  # we need to reference this within the class
        self.redis_exception = redis.exceptions.ConnectionError
        self.redis_connection = None

    def __call__(self, environ, start_response):

        def _start_response(status, response_headers, exc_info=None):
            # This wrapper allows us to get the status and headers.
            environ['CKAN_PAGE_STATUS'] = status
            environ['CKAN_PAGE_HEADERS'] = response_headers
            return start_response(status, response_headers, exc_info)

        # Only use cache for GET requests
        # REMOTE_USER is used by some tests.
        if environ['REQUEST_METHOD'] != 'GET' or environ.get('REMOTE_USER'):
            return self.app(environ, start_response)

        # If there is a ckan cookie (or auth_tkt) we avoid the cache.
        # We want to allow other cookies like google analytics ones :(
        cookie_string = environ.get('HTTP_COOKIE')
        if cookie_string:
            for cookie in cookie_string.split(';'):
                if cookie.startswith('ckan') or cookie.startswith('auth_tkt'):
                    return self.app(environ, start_response)

        # Make our cache key
        key = 'page:%s?%s' % (environ['PATH_INFO'], environ['QUERY_STRING'])

        # Try to connect if we don't have a connection. Doing this here
        # allows the redis server to be unavailable at times.
        if self.redis_connection is None:
            try:
                self.redis_connection = self.redis.StrictRedis()
                self.redis_connection.flushdb()
            except self.redis_exception:
                # Connection may have failed at flush so clear it.
                self.redis_connection = None
                return self.app(environ, start_response)

        # If cached return cached result
        try:
            result = self.redis_connection.lrange(key, 0, 2)
        except self.redis_exception:
            # Connection failed so clear it and return the page as normal.
            self.redis_connection = None
            return self.app(environ, start_response)

        if result:
            headers = json.loads(result[1])
            # Convert headers from list to tuples.
            headers = [(str(key), str(value)) for key, value in headers]
            start_response(str(result[0]), headers)
            # Returning a huge string slows down the server. Therefore we
            # cut it up into more usable chunks.
            page = result[2]
            out = []
            total = len(page)
            position = 0
            size = 4096
            while position < total:
                out.append(page[position:position + size])
                position += size
            return out

        # Generate the response from our application.
        page = self.app(environ, _start_response)

        # Only cache http status 200 pages
        if not environ['CKAN_PAGE_STATUS'].startswith('200'):
            return page

        cachable = False
        if environ.get('CKAN_PAGE_CACHABLE'):
            cachable = True

        # Cache things if cachable.
        if cachable:
            # Make sure we consume any file handles etc.
            page_string = ''.join(list(page))
            # Use a pipe to add page in a transaction.
            pipe = self.redis_connection.pipeline()
            pipe.rpush(key, environ['CKAN_PAGE_STATUS'])
            pipe.rpush(key, json.dumps(environ['CKAN_PAGE_HEADERS']))
            pipe.rpush(key, page_string)
            pipe.execute()
        return page


class TrackingMiddleware(object):

    def __init__(self, app, config):
        self.app = app
        self.engine = sa.create_engine(config.get('sqlalchemy.url'))

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        method = environ.get('REQUEST_METHOD')
        if path == '/_tracking' and method == 'POST':
            # do the tracking
            # get the post data
            payload = environ['wsgi.input'].read()
            parts = payload.split('&')
            data = {}
            for part in parts:
                k, v = part.split('=')
                data[k] = urllib2.unquote(v).decode("utf8")
            start_response('200 OK', [('Content-Type', 'text/html')])
            # we want a unique anonomized key for each user so that we do
            # not count multiple clicks from the same user.
            key = ''.join([
                environ['HTTP_USER_AGENT'],
                environ['REMOTE_ADDR'],
                environ.get('HTTP_ACCEPT_LANGUAGE', ''),
                environ.get('HTTP_ACCEPT_ENCODING', ''),
            ])
            key = hashlib.md5(key).hexdigest()
            # store key/data here
            sql = '''INSERT INTO tracking_raw
                     (user_key, url, tracking_type)
                     VALUES (%s, %s, %s)'''
            self.engine.execute(sql, key, data.get('url'), data.get('type'))
            return []
        return self.app(environ, start_response)


class HostHeaderMiddleware(object):
    '''
        Prevent the `Host` header from the incoming request to be used
        in the `Location` header of a redirect.
    '''
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        path_info = environ[u'PATH_INFO']
        if path_info in ['/login_generic', '/user/login',
                         '/user/logout', '/user/logged_in',
                         '/user/logged_out']:
            site_url = config.get('ckan.site_url')
            parts = urlparse(site_url)
            environ['HTTP_HOST'] = parts.netloc
        return self.app(environ, start_response)
