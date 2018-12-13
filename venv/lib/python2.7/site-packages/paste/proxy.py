# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
An application that proxies WSGI requests to a remote server.

TODO:

* Send ``Via`` header?  It's not clear to me this is a Via in the
  style of a typical proxy.

* Other headers or metadata?  I put in X-Forwarded-For, but that's it.

* Signed data of non-HTTP keys?  This would be for things like
  REMOTE_USER.

* Something to indicate what the original URL was?  The original host,
  scheme, and base path.

* Rewriting ``Location`` headers?  mod_proxy does this.

* Rewriting body?  (Probably not on this one -- that can be done with
  a different middleware that wraps this middleware)

* Example::  
    
    use = egg:Paste#proxy
    address = http://server3:8680/exist/rest/db/orgs/sch/config/
    allowed_request_methods = GET
  
"""

import httplib
import urlparse
import urllib

from paste import httpexceptions
from paste.util.converters import aslist

# Remove these headers from response (specify lower case header
# names):
filtered_headers = (     
    'transfer-encoding',
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailers',
    'upgrade',
)

class Proxy(object):

    def __init__(self, address, allowed_request_methods=(),
                 suppress_http_headers=()):
        self.address = address
        self.parsed = urlparse.urlsplit(address)
        self.scheme = self.parsed[0].lower()
        self.host = self.parsed[1]
        self.path = self.parsed[2]
        self.allowed_request_methods = [
            x.lower() for x in allowed_request_methods if x]
        
        self.suppress_http_headers = [
            x.lower() for x in suppress_http_headers if x]

    def __call__(self, environ, start_response):
        if (self.allowed_request_methods and 
            environ['REQUEST_METHOD'].lower() not in self.allowed_request_methods):
            return httpexceptions.HTTPBadRequest("Disallowed")(environ, start_response)

        if self.scheme == 'http':
            ConnClass = httplib.HTTPConnection
        elif self.scheme == 'https':
            ConnClass = httplib.HTTPSConnection
        else:
            raise ValueError(
                "Unknown scheme for %r: %r" % (self.address, self.scheme))
        conn = ConnClass(self.host)
        headers = {}
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                key = key[5:].lower().replace('_', '-')
                if key == 'host' or key in self.suppress_http_headers:
                    continue
                headers[key] = value
        headers['host'] = self.host
        if 'REMOTE_ADDR' in environ:
            headers['x-forwarded-for'] = environ['REMOTE_ADDR']
        if environ.get('CONTENT_TYPE'):
            headers['content-type'] = environ['CONTENT_TYPE']
        if environ.get('CONTENT_LENGTH'):
            if environ['CONTENT_LENGTH'] == '-1':
                # This is a special case, where the content length is basically undetermined
                body = environ['wsgi.input'].read(-1)
                headers['content-length'] = str(len(body))
            else:
                headers['content-length'] = environ['CONTENT_LENGTH'] 
                length = int(environ['CONTENT_LENGTH'])
                body = environ['wsgi.input'].read(length)
        else:
            body = ''
            
        path_info = urllib.quote(environ['PATH_INFO'])
        if self.path:            
            request_path = path_info
            if request_path and request_path[0] == '/':
                request_path = request_path[1:]
                
            path = urlparse.urljoin(self.path, request_path)
        else:
            path = path_info
        if environ.get('QUERY_STRING'):
            path += '?' + environ['QUERY_STRING']
            
        conn.request(environ['REQUEST_METHOD'],
                     path,
                     body, headers)
        res = conn.getresponse()
        headers_out = parse_headers(res.msg)
        
        status = '%s %s' % (res.status, res.reason)
        start_response(status, headers_out)
        # @@: Default?
        length = res.getheader('content-length')
        if length is not None:
            body = res.read(int(length))
        else:
            body = res.read()
        conn.close()
        return [body]

def make_proxy(global_conf, address, allowed_request_methods="",
               suppress_http_headers=""):
    """
    Make a WSGI application that proxies to another address:
    
    ``address``
        the full URL ending with a trailing ``/``
        
    ``allowed_request_methods``:
        a space seperated list of request methods (e.g., ``GET POST``)
        
    ``suppress_http_headers``
        a space seperated list of http headers (lower case, without
        the leading ``http_``) that should not be passed on to target
        host
    """
    allowed_request_methods = aslist(allowed_request_methods)
    suppress_http_headers = aslist(suppress_http_headers)
    return Proxy(
        address,
        allowed_request_methods=allowed_request_methods,
        suppress_http_headers=suppress_http_headers)


class TransparentProxy(object):

    """
    A proxy that sends the request just as it was given, including
    respecting HTTP_HOST, wsgi.url_scheme, etc.

    This is a way of translating WSGI requests directly to real HTTP
    requests.  All information goes in the environment; modify it to
    modify the way the request is made.

    If you specify ``force_host`` (and optionally ``force_scheme``)
    then HTTP_HOST won't be used to determine where to connect to;
    instead a specific host will be connected to, but the ``Host``
    header in the request will remain intact.
    """

    def __init__(self, force_host=None,
                 force_scheme='http'):
        self.force_host = force_host
        self.force_scheme = force_scheme

    def __repr__(self):
        return '<%s %s force_host=%r force_scheme=%r>' % (
            self.__class__.__name__,
            hex(id(self)),
            self.force_host, self.force_scheme)

    def __call__(self, environ, start_response):
        scheme = environ['wsgi.url_scheme']
        if self.force_host is None:
            conn_scheme = scheme
        else:
            conn_scheme = self.force_scheme
        if conn_scheme == 'http':
            ConnClass = httplib.HTTPConnection
        elif conn_scheme == 'https':
            ConnClass = httplib.HTTPSConnection
        else:
            raise ValueError(
                "Unknown scheme %r" % scheme)
        if 'HTTP_HOST' not in environ:
            raise ValueError(
                "WSGI environ must contain an HTTP_HOST key")
        host = environ['HTTP_HOST']
        if self.force_host is None:
            conn_host = host
        else:
            conn_host = self.force_host
        conn = ConnClass(conn_host)
        headers = {}
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                key = key[5:].lower().replace('_', '-')
                headers[key] = value
        headers['host'] = host
        if 'REMOTE_ADDR' in environ and 'HTTP_X_FORWARDED_FOR' not in environ:
            headers['x-forwarded-for'] = environ['REMOTE_ADDR']
        if environ.get('CONTENT_TYPE'):
            headers['content-type'] = environ['CONTENT_TYPE']
        if environ.get('CONTENT_LENGTH'):
            length = int(environ['CONTENT_LENGTH'])
            body = environ['wsgi.input'].read(length)
            if length == -1:
                environ['CONTENT_LENGTH'] = str(len(body))
        elif 'CONTENT_LENGTH' not in environ:
            body = ''
            length = 0
        else:
            body = ''
            length = 0
        
        path = (environ.get('SCRIPT_NAME', '')
                + environ.get('PATH_INFO', ''))
        path = urllib.quote(path)
        if 'QUERY_STRING' in environ:
            path += '?' + environ['QUERY_STRING']
        conn.request(environ['REQUEST_METHOD'],
                     path, body, headers)
        res = conn.getresponse()
        headers_out = parse_headers(res.msg)
                
        status = '%s %s' % (res.status, res.reason)
        start_response(status, headers_out)
        # @@: Default?
        length = res.getheader('content-length')
        if length is not None:
            body = res.read(int(length))
        else:
            body = res.read()
        conn.close()
        return [body]

def parse_headers(message):
    """
    Turn a Message object into a list of WSGI-style headers.
    """
    headers_out = []        
    for full_header in message.headers:
        if not full_header:            
            # Shouldn't happen, but we'll just ignore
            continue                     
        if full_header[0].isspace():
            # Continuation line, add to the last header
            if not headers_out:                        
                raise ValueError(
                    "First header starts with a space (%r)" % full_header)
            last_header, last_value = headers_out.pop()                   
            value = last_value + ' ' + full_header.strip()
            headers_out.append((last_header, value))      
            continue                                
        try:        
            header, value = full_header.split(':', 1)
        except:                                      
            raise ValueError("Invalid header: %r" % full_header)
        value = value.strip()                                   
        if header.lower() not in filtered_headers:
            headers_out.append((header, value))   
    return headers_out

def make_transparent_proxy(
    global_conf, force_host=None, force_scheme='http'):
    """
    Create a proxy that connects to a specific host, but does
    absolutely no other filtering, including the Host header.
    """
    return TransparentProxy(force_host=force_host,
                            force_scheme=force_scheme)
