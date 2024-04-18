# encoding: utf-8

"""Additional middleware used by the Flask app stack."""
from typing import Any

from urllib.parse import urlparse

from ckan.common import config
from ckan.types import CKANApp


class RootPathMiddleware(object):
    '''
    Prevents the SCRIPT_NAME server variable conflicting with the ckan.root_url
    config. The routes package uses the SCRIPT_NAME variable and appends to the
    path and ckan adds the root url causing a duplication of the root path.
    This is a middleware to ensure that even redirects use this logic.
    '''
    def __init__(self, app: CKANApp):
        self.app = app

    def __call__(self, environ: Any, start_response: Any):
        # Prevents the variable interfering with the root_path logic
        if 'SCRIPT_NAME' in environ:
            environ['SCRIPT_NAME'] = ''

        return self.app(environ, start_response)


class HostHeaderMiddleware(object):
    '''
        Prevent the `Host` header from the incoming request to be used
        in the `Location` header of a redirect.
    '''
    def __init__(self, app: CKANApp):
        self.app = app

    def __call__(self, environ: Any, start_response: Any) -> Any:
        path_info = environ[u'PATH_INFO']
        if path_info in ['/login_generic', '/user/login',
                         '/user/logout', '/user/logged_in',
                         '/user/logged_out']:
            site_url = config.get('ckan.site_url')
            parts = urlparse(site_url)
            environ['HTTP_HOST'] = str(parts.netloc)
        return self.app(environ, start_response)
