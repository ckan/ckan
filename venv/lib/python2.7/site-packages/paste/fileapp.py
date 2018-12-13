# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
# (c) 2005 Ian Bicking, Clark C. Evans and contributors
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
"""
This module handles sending static content such as in-memory data or
files.  At this time it has cache helpers and understands the
if-modified-since request header.
"""

import os, time, mimetypes, zipfile, tarfile
from paste.httpexceptions import *
from paste.httpheaders import *

CACHE_SIZE = 4096
BLOCK_SIZE = 4096 * 16

__all__ = ['DataApp', 'FileApp', 'DirectoryApp', 'ArchiveStore']

class DataApp(object):
    """
    Returns an application that will send content in a single chunk,
    this application has support for setting cache-control and for
    responding to conditional (or HEAD) requests.

    Constructor Arguments:

        ``content``     the content being sent to the client

        ``headers``     the headers to send /w the response

        The remaining ``kwargs`` correspond to headers, where the
        underscore is replaced with a dash.  These values are only
        added to the headers if they are not already provided; thus,
        they can be used for default values.  Examples include, but
        are not limited to:

            ``content_type``
            ``content_encoding``
            ``content_location``

    ``cache_control()``

        This method provides validated construction of the ``Cache-Control``
        header as well as providing for automated filling out of the
        ``EXPIRES`` header for HTTP/1.0 clients.

    ``set_content()``

        This method provides a mechanism to set the content after the
        application has been constructed.  This method does things
        like changing ``Last-Modified`` and ``Content-Length`` headers.

    """

    allowed_methods = ('GET', 'HEAD')

    def __init__(self, content, headers=None, allowed_methods=None,
                 **kwargs):
        assert isinstance(headers, (type(None), list))
        self.expires = None
        self.content = None
        self.content_length = None
        self.last_modified = 0
        if allowed_methods is not None:
            self.allowed_methods = allowed_methods
        self.headers = headers or []
        for (k, v) in kwargs.items():
            header = get_header(k)
            header.update(self.headers, v)
        ACCEPT_RANGES.update(self.headers, bytes=True)
        if not CONTENT_TYPE(self.headers):
            CONTENT_TYPE.update(self.headers)
        if content is not None:
            self.set_content(content)

    def cache_control(self, **kwargs):
        self.expires = CACHE_CONTROL.apply(self.headers, **kwargs) or None
        return self

    def set_content(self, content, last_modified=None):
        assert content is not None
        if last_modified is None:
            self.last_modified = time.time()
        else:
            self.last_modified = last_modified
        self.content = content
        self.content_length = len(content)
        LAST_MODIFIED.update(self.headers, time=self.last_modified)
        return self

    def content_disposition(self, **kwargs):
        CONTENT_DISPOSITION.apply(self.headers, **kwargs)
        return self

    def __call__(self, environ, start_response):
        method = environ['REQUEST_METHOD'].upper()
        if method not in self.allowed_methods:
            exc = HTTPMethodNotAllowed(
                'You cannot %s a file' % method,
                headers=[('Allow', ','.join(self.allowed_methods))])
            return exc(environ, start_response)
        return self.get(environ, start_response)

    def calculate_etag(self):
        return '"%s-%s"' % (self.last_modified, self.content_length)

    def get(self, environ, start_response):
        headers = self.headers[:]
        current_etag = self.calculate_etag()
        ETAG.update(headers, current_etag)
        if self.expires is not None:
            EXPIRES.update(headers, delta=self.expires)

        try:
            client_etags = IF_NONE_MATCH.parse(environ)
            if client_etags:
                for etag in client_etags:
                    if etag == current_etag or etag == '*':
                        # horribly inefficient, n^2 performance, yuck!
                        for head in list_headers(entity=True):
                            head.delete(headers)
                        start_response('304 Not Modified', headers)
                        return ['']
        except HTTPBadRequest, exce:
            return exce.wsgi_application(environ, start_response)

        # If we get If-None-Match and If-Modified-Since, and
        # If-None-Match doesn't match, then we should not try to
        # figure out If-Modified-Since (which has 1-second granularity
        # and just isn't as accurate)
        if not client_etags:
            try:
                client_clock = IF_MODIFIED_SINCE.parse(environ)
                if client_clock >= int(self.last_modified):
                    # horribly inefficient, n^2 performance, yuck!
                    for head in list_headers(entity=True):
                        head.delete(headers)
                    start_response('304 Not Modified', headers)
                    return [''] # empty body
            except HTTPBadRequest, exce:
                return exce.wsgi_application(environ, start_response)

        (lower, upper) = (0, self.content_length - 1)
        range = RANGE.parse(environ)
        if range and 'bytes' == range[0] and 1 == len(range[1]):
            (lower, upper) = range[1][0]
            upper = upper or (self.content_length - 1)
            if upper >= self.content_length or lower > upper:
                return HTTPRequestRangeNotSatisfiable((
                  "Range request was made beyond the end of the content,\r\n"
                  "which is %s long.\r\n  Range: %s\r\n") % (
                     self.content_length, RANGE(environ))
                ).wsgi_application(environ, start_response)

        content_length = upper - lower + 1
        CONTENT_RANGE.update(headers, first_byte=lower, last_byte=upper,
                            total_length = self.content_length)
        CONTENT_LENGTH.update(headers, content_length)
        if content_length == self.content_length:
            start_response('200 OK', headers)
        else:
            start_response('206 Partial Content', headers)
        if self.content is not None:
            return [self.content[lower:upper+1]]
        return (lower, content_length)

class FileApp(DataApp):
    """
    Returns an application that will send the file at the given
    filename.  Adds a mime type based on ``mimetypes.guess_type()``.
    See DataApp for the arguments beyond ``filename``.
    """

    def __init__(self, filename, headers=None, **kwargs):
        self.filename = filename
        content_type, content_encoding = self.guess_type()
        if content_type and 'content_type' not in kwargs:
            kwargs['content_type'] = content_type
        if content_encoding and 'content_encoding' not in kwargs:
            kwargs['content_encoding'] = content_encoding
        DataApp.__init__(self, None, headers, **kwargs)

    def guess_type(self):
        return mimetypes.guess_type(self.filename)

    def update(self, force=False):
        stat = os.stat(self.filename)
        if not force and stat.st_mtime == self.last_modified:
            return
        self.last_modified = stat.st_mtime
        if stat.st_size < CACHE_SIZE:
            fh = open(self.filename,"rb")
            self.set_content(fh.read(), stat.st_mtime)
            fh.close()
        else:
            self.content = None
            self.content_length = stat.st_size
            # This is updated automatically if self.set_content() is
            # called
            LAST_MODIFIED.update(self.headers, time=self.last_modified)

    def get(self, environ, start_response):
        is_head = environ['REQUEST_METHOD'].upper() == 'HEAD'
        if 'max-age=0' in CACHE_CONTROL(environ).lower():
            self.update(force=True) # RFC 2616 13.2.6
        else:
            self.update()
        if not self.content:
            if not os.path.exists(self.filename):
                exc = HTTPNotFound(
                    'The resource does not exist',
                    comment="No file at %r" % self.filename)
                return exc(environ, start_response)
            try:
                file = open(self.filename, 'rb')
            except (IOError, OSError), e:
                exc = HTTPForbidden(
                    'You are not permitted to view this file (%s)' % e)
                return exc.wsgi_application(
                    environ, start_response)
        retval = DataApp.get(self, environ, start_response)
        if isinstance(retval, list):
            # cached content, exception, or not-modified
            if is_head:
                return ['']
            return retval
        (lower, content_length) = retval
        if is_head:
            return ['']
        file.seek(lower)
        file_wrapper = environ.get('wsgi.file_wrapper', None)
        if file_wrapper:
            return file_wrapper(file, BLOCK_SIZE)
        else:
            return _FileIter(file, size=content_length)

class _FileIter(object):

    def __init__(self, file, block_size=None, size=None):
        self.file = file
        self.size = size
        self.block_size = block_size or BLOCK_SIZE

    def __iter__(self):
        return self

    def next(self):
        chunk_size = self.block_size
        if self.size is not None:
            if chunk_size > self.size:
                chunk_size = self.size
            self.size -= chunk_size
        data = self.file.read(chunk_size)
        if not data:
            raise StopIteration
        return data

    def close(self):
        self.file.close()


class DirectoryApp(object):
    """
    Returns an application that dispatches requests to corresponding FileApps based on PATH_INFO.
    FileApp instances are cached. This app makes sure not to serve any files that are not in a subdirectory.
    To customize FileApp creation override ``DirectoryApp.make_fileapp``
    """

    def __init__(self, path):
        self.path = os.path.abspath(path)
        if not self.path.endswith(os.path.sep):
            self.path += os.path.sep
        assert os.path.isdir(self.path)
        self.cached_apps = {}

    make_fileapp = FileApp

    def __call__(self, environ, start_response):
        path_info = environ['PATH_INFO']
        app = self.cached_apps.get(path_info)
        if app is None:
            path = os.path.join(self.path, path_info.lstrip('/'))
            if not os.path.normpath(path).startswith(self.path):
                app = HTTPForbidden()
            elif os.path.isfile(path):
                app = self.make_fileapp(path)
                self.cached_apps[path_info] = app
            else:
                app = HTTPNotFound(comment=path)
        return app(environ, start_response)


class ArchiveStore(object):
    """
    Returns an application that serves up a DataApp for items requested
    in a given zip or tar archive.

    Constructor Arguments:

        ``filepath``    the path to the archive being served

    ``cache_control()``

        This method provides validated construction of the ``Cache-Control``
        header as well as providing for automated filling out of the
        ``EXPIRES`` header for HTTP/1.0 clients.
    """

    def __init__(self, filepath):
        if zipfile.is_zipfile(filepath):
            self.archive = zipfile.ZipFile(filepath,"r")
        elif tarfile.is_tarfile(filepath):
            self.archive = tarfile.TarFileCompat(filepath,"r")
        else:
            raise AssertionError("filepath '%s' is not a zip or tar " % filepath)
        self.expires = None
        self.last_modified = time.time()
        self.cache = {}

    def cache_control(self, **kwargs):
        self.expires = CACHE_CONTROL.apply(self.headers, **kwargs) or None
        return self

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO","")
        if path.startswith("/"):
            path = path[1:]
        application = self.cache.get(path)
        if application:
            return application(environ, start_response)
        try:
            info = self.archive.getinfo(path)
        except KeyError:
            exc = HTTPNotFound("The file requested, '%s', was not found." % path)
            return exc.wsgi_application(environ, start_response)
        if info.filename.endswith("/"):
            exc = HTTPNotFound("Path requested, '%s', is not a file." % path)
            return exc.wsgi_application(environ, start_response)
        content_type, content_encoding = mimetypes.guess_type(info.filename)
        # 'None' is not a valid content-encoding, so don't set the header if
        # mimetypes.guess_type returns None
        if content_encoding is not None:
            app = DataApp(None, content_type = content_type,
                                content_encoding = content_encoding)
        else:
            app = DataApp(None, content_type = content_type)
        app.set_content(self.archive.read(path),
                time.mktime(info.date_time + (0,0,0)))
        self.cache[path] = app
        app.expires = self.expires
        return app(environ, start_response)

