# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Map URL prefixes to WSGI applications.  See ``URLMap``
"""

from UserDict import DictMixin
import re
import os
import cgi
from paste import httpexceptions

__all__ = ['URLMap', 'PathProxyURLMap']

def urlmap_factory(loader, global_conf, **local_conf):
    if 'not_found_app' in local_conf:
        not_found_app = local_conf.pop('not_found_app')
    else:
        not_found_app = global_conf.get('not_found_app')
    if not_found_app:
        not_found_app = loader.get_app(not_found_app, global_conf=global_conf)
    urlmap = URLMap(not_found_app=not_found_app)
    for path, app_name in local_conf.items():
        path = parse_path_expression(path)
        app = loader.get_app(app_name, global_conf=global_conf)
        urlmap[path] = app
    return urlmap

def parse_path_expression(path):
    """
    Parses a path expression like 'domain foobar.com port 20 /' or
    just '/foobar' for a path alone.  Returns as an address that
    URLMap likes.
    """
    parts = path.split()
    domain = port = path = None
    while parts:
        if parts[0] == 'domain':
            parts.pop(0)
            if not parts:
                raise ValueError("'domain' must be followed with a domain name")
            if domain:
                raise ValueError("'domain' given twice")
            domain = parts.pop(0)
        elif parts[0] == 'port':
            parts.pop(0)
            if not parts:
                raise ValueError("'port' must be followed with a port number")
            if port:
                raise ValueError("'port' given twice")
            port = parts.pop(0)
        else:
            if path:
                raise ValueError("more than one path given (have %r, got %r)"
                                 % (path, parts[0]))
            path = parts.pop(0)
    s = ''
    if domain:
        s = 'http://%s' % domain
    if port:
        if not domain:
            raise ValueError("If you give a port, you must also give a domain")
        s += ':' + port
    if path:
        if s:
            s += '/'
        s += path
    return s

class URLMap(DictMixin):

    """
    URLMap instances are dictionary-like object that dispatch to one
    of several applications based on the URL.

    The dictionary keys are URLs to match (like
    ``PATH_INFO.startswith(url)``), and the values are applications to
    dispatch to.  URLs are matched most-specific-first, i.e., longest
    URL first.  The ``SCRIPT_NAME`` and ``PATH_INFO`` environmental
    variables are adjusted to indicate the new context.

    URLs can also include domains, like ``http://blah.com/foo``, or as
    tuples ``('blah.com', '/foo')``.  This will match domain names; without
    the ``http://domain`` or with a domain of ``None`` any domain will be
    matched (so long as no other explicit domain matches).  """

    def __init__(self, not_found_app=None):
        self.applications = []
        if not not_found_app:
            not_found_app = self.not_found_app
        self.not_found_application = not_found_app

    norm_url_re = re.compile('//+')
    domain_url_re = re.compile('^(http|https)://')

    def not_found_app(self, environ, start_response):
        mapper = environ.get('paste.urlmap_object')
        if mapper:
            matches = [p for p, a in mapper.applications]
            extra = 'defined apps: %s' % (
                ',\n  '.join(map(repr, matches)))
        else:
            extra = ''
        extra += '\nSCRIPT_NAME: %r' % environ.get('SCRIPT_NAME')
        extra += '\nPATH_INFO: %r' % environ.get('PATH_INFO')
        extra += '\nHTTP_HOST: %r' % environ.get('HTTP_HOST')
        app = httpexceptions.HTTPNotFound(
            environ['PATH_INFO'],
            comment=cgi.escape(extra)).wsgi_application
        return app(environ, start_response)

    def normalize_url(self, url, trim=True):
        if isinstance(url, (list, tuple)):
            domain = url[0]
            url = self.normalize_url(url[1])[1]
            return domain, url
        assert (not url or url.startswith('/')
                or self.domain_url_re.search(url)), (
            "URL fragments must start with / or http:// (you gave %r)" % url)
        match = self.domain_url_re.search(url)
        if match:
            url = url[match.end():]
            if '/' in url:
                domain, url = url.split('/', 1)
                url = '/' + url
            else:
                domain, url = url, ''
        else:
            domain = None
        url = self.norm_url_re.sub('/', url)
        if trim:
            url = url.rstrip('/')
        return domain, url

    def sort_apps(self):
        """
        Make sure applications are sorted with longest URLs first
        """
        def key(app_desc):
            (domain, url), app = app_desc
            if not domain:
                # Make sure empty domains sort last:
                return '\xff', -len(url)
            else:
                return domain, -len(url)
        apps = [(key(desc), desc) for desc in self.applications]
        apps.sort()
        self.applications = [desc for (sortable, desc) in apps]

    def __setitem__(self, url, app):
        if app is None:
            try:
                del self[url]
            except KeyError:
                pass
            return
        dom_url = self.normalize_url(url)
        if dom_url in self:
            del self[dom_url]
        self.applications.append((dom_url, app))
        self.sort_apps()

    def __getitem__(self, url):
        dom_url = self.normalize_url(url)
        for app_url, app in self.applications:
            if app_url == dom_url:
                return app
        raise KeyError(
            "No application with the url %r (domain: %r; existing: %s)"
            % (url[1], url[0] or '*', self.applications))

    def __delitem__(self, url):
        url = self.normalize_url(url)
        for app_url, app in self.applications:
            if app_url == url:
                self.applications.remove((app_url, app))
                break
        else:
            raise KeyError(
                "No application with the url %r" % (url,))

    def keys(self):
        return [app_url for app_url, app in self.applications]

    def __call__(self, environ, start_response):
        host = environ.get('HTTP_HOST', environ.get('SERVER_NAME')).lower()
        if ':' in host:
            host, port = host.split(':', 1)
        else:
            if environ['wsgi.url_scheme'] == 'http':
                port = '80'
            else:
                port = '443'
        path_info = environ.get('PATH_INFO')
        path_info = self.normalize_url(path_info, False)[1]
        for (domain, app_url), app in self.applications:
            if domain and domain != host and domain != host+':'+port:
                continue
            if (path_info == app_url
                or path_info.startswith(app_url + '/')):
                environ['SCRIPT_NAME'] += app_url
                environ['PATH_INFO'] = path_info[len(app_url):]
                return app(environ, start_response)
        environ['paste.urlmap_object'] = self
        return self.not_found_application(environ, start_response)


class PathProxyURLMap(object):

    """
    This is a wrapper for URLMap that catches any strings that
    are passed in as applications; these strings are treated as
    filenames (relative to `base_path`) and are passed to the
    callable `builder`, which will return an application.

    This is intended for cases when configuration files can be
    treated as applications.

    `base_paste_url` is the URL under which all applications added through
    this wrapper must go.  Use ``""`` if you want this to not
    change incoming URLs.
    """

    def __init__(self, map, base_paste_url, base_path, builder):
        self.map = map
        self.base_paste_url = self.map.normalize_url(base_paste_url)
        self.base_path = base_path
        self.builder = builder

    def __setitem__(self, url, app):
        if isinstance(app, (str, unicode)):
            app_fn = os.path.join(self.base_path, app)
            app = self.builder(app_fn)
        url = self.map.normalize_url(url)
        # @@: This means http://foo.com/bar will potentially
        # match foo.com, but /base_paste_url/bar, which is unintuitive
        url = (url[0] or self.base_paste_url[0],
               self.base_paste_url[1] + url[1])
        self.map[url] = app

    def __getattr__(self, attr):
        return getattr(self.map, attr)

    # This is really the only settable attribute
    def not_found_application__get(self):
        return self.map.not_found_application
    def not_found_application__set(self, value):
        self.map.not_found_application = value
    not_found_application = property(not_found_application__get,
                                     not_found_application__set)
