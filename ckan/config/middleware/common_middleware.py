# encoding: utf-8

"""Common middleware used by both Flask and Pylons app stacks."""
import hashlib
import cgi

import six
from six.moves.urllib.parse import unquote, urlparse

import sqlalchemy as sa
from webob.request import FakeCGIBody

from ckan.common import config
from ckan.lib.i18n import get_locales_from_config


class CloseWSGIInputMiddleware(object):
    '''
    webob.request.Request has habit to create FakeCGIBody. This leads(
    during file upload) to creating temporary files that are not closed.
    For long lived processes this means that for each upload you will
    spend the same amount of temporary space as size of uploaded
    file additionally, until server restart(this will automatically
    close temporary files).

    This middleware is supposed to close such files after each request.
    '''
    def __init__(self, app, config):
        self.app = app

    def __call__(self, environ, start_response):
        wsgi_input = environ['wsgi.input']
        if isinstance(wsgi_input, FakeCGIBody):
            for _, item in wsgi_input.vars.items():
                if not isinstance(item, cgi.FieldStorage):
                    continue
                fp = getattr(item, 'fp', None)
                if fp is not None:
                    fp.close()
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
            payload = six.ensure_str(environ['wsgi.input'].read())
            parts = payload.split('&')
            data = {}
            for part in parts:
                k, v = part.split('=')
                data[k] = unquote(v)
            start_response('200 OK', [('Content-Type', 'text/html')])
            # we want a unique anonomized key for each user so that we do
            # not count multiple clicks from the same user.
            key = ''.join([
                environ['HTTP_USER_AGENT'],
                environ['REMOTE_ADDR'],
                environ.get('HTTP_ACCEPT_LANGUAGE', ''),
                environ.get('HTTP_ACCEPT_ENCODING', ''),
            ])
            key = hashlib.md5(six.ensure_binary(key)).hexdigest()
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
            environ['HTTP_HOST'] = str(parts.netloc)
        return self.app(environ, start_response)
