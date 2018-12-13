# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

"""
WSGI middleware

Gzip-encodes the response.
"""

import gzip
from paste.response import header_value, remove_header
from paste.httpheaders import CONTENT_LENGTH

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

class GzipOutput(object):
    pass

class middleware(object):

    def __init__(self, application, compress_level=6):
        self.application = application
        self.compress_level = int(compress_level)

    def __call__(self, environ, start_response):
        if 'gzip' not in environ.get('HTTP_ACCEPT_ENCODING', ''):
            # nothing for us to do, so this middleware will
            # be a no-op:
            return self.application(environ, start_response)
        response = GzipResponse(start_response, self.compress_level)
        app_iter = self.application(environ,
                                    response.gzip_start_response)
        if app_iter is not None:
            response.finish_response(app_iter)

        return response.write()

class GzipResponse(object):

    def __init__(self, start_response, compress_level):
        self.start_response = start_response
        self.compress_level = compress_level
        self.buffer = StringIO()
        self.compressible = False
        self.content_length = None

    def gzip_start_response(self, status, headers, exc_info=None):
        self.headers = headers
        ct = header_value(headers,'content-type')
        ce = header_value(headers,'content-encoding')
        self.compressible = False
        if ct and (ct.startswith('text/') or ct.startswith('application/')) \
            and 'zip' not in ct:
            self.compressible = True
        if ce:
            self.compressible = False
        if self.compressible:
            headers.append(('content-encoding', 'gzip'))
        remove_header(headers, 'content-length')
        self.headers = headers
        self.status = status
        return self.buffer.write

    def write(self):
        out = self.buffer
        out.seek(0)
        s = out.getvalue()
        out.close()
        return [s]

    def finish_response(self, app_iter):
        if self.compressible:
            output = gzip.GzipFile(mode='wb', compresslevel=self.compress_level,
                fileobj=self.buffer)
        else:
            output = self.buffer
        try:
            for s in app_iter:
                output.write(s)
            if self.compressible:
                output.close()
        finally:
            if hasattr(app_iter, 'close'):
                app_iter.close()
        content_length = self.buffer.tell()
        CONTENT_LENGTH.update(self.headers, content_length)
        self.start_response(self.status, self.headers)

def filter_factory(application, **conf):
    import warnings
    warnings.warn(
        'This function is deprecated; use make_gzip_middleware instead',
        DeprecationWarning, 2)
    def filter(application):
        return middleware(application)
    return filter

def make_gzip_middleware(app, global_conf, compress_level=6):
    """
    Wrap the middleware, so that it applies gzipping to a response
    when it is supported by the browser and the content is of
    type ``text/*`` or ``application/*``
    """
    compress_level = int(compress_level)
    return middleware(app, compress_level=compress_level)
