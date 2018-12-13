# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# This code was written with funding by http://prometheusresearch.com
"""
Upload Progress Monitor

This is a WSGI middleware component which monitors the status of files
being uploaded.  It includes a small query application which will return
a list of all files being uploaded by particular session/user.

>>> from paste.httpserver import serve
>>> from paste.urlmap import URLMap
>>> from paste.auth.basic import AuthBasicHandler
>>> from paste.debug.debugapp import SlowConsumer, SimpleApplication
>>> # from paste.progress import *
>>> realm = 'Test Realm'
>>> def authfunc(username, password):
...     return username == password
>>> map = URLMap({})
>>> ups = UploadProgressMonitor(map, threshold=1024)
>>> map['/upload'] = SlowConsumer()
>>> map['/simple'] = SimpleApplication()
>>> map['/report'] = UploadProgressReporter(ups)
>>> serve(AuthBasicHandler(ups, realm, authfunc))
serving on...

.. note::

   This is experimental, and will change in the future.
"""
import time
from paste.wsgilib import catch_errors

DEFAULT_THRESHOLD = 1024 * 1024  # one megabyte
DEFAULT_TIMEOUT   = 60*5         # five minutes
ENVIRON_RECEIVED  = 'paste.bytes_received'
REQUEST_STARTED   = 'paste.request_started'
REQUEST_FINISHED  = 'paste.request_finished'

class _ProgressFile(object):
    """
    This is the input-file wrapper used to record the number of
    ``paste.bytes_received`` for the given request.
    """

    def __init__(self, environ, rfile):
        self._ProgressFile_environ = environ
        self._ProgressFile_rfile   = rfile
        self.flush = rfile.flush
        self.write = rfile.write
        self.writelines = rfile.writelines

    def __iter__(self):
        environ = self._ProgressFile_environ
        riter = iter(self._ProgressFile_rfile)
        def iterwrap():
            for chunk in riter:
                environ[ENVIRON_RECEIVED] += len(chunk)
                yield chunk
        return iter(iterwrap)

    def read(self, size=-1):
        chunk = self._ProgressFile_rfile.read(size)
        self._ProgressFile_environ[ENVIRON_RECEIVED] += len(chunk)
        return chunk

    def readline(self):
        chunk = self._ProgressFile_rfile.readline()
        self._ProgressFile_environ[ENVIRON_RECEIVED] += len(chunk)
        return chunk

    def readlines(self, hint=None):
        chunk = self._ProgressFile_rfile.readlines(hint)
        self._ProgressFile_environ[ENVIRON_RECEIVED] += len(chunk)
        return chunk

class UploadProgressMonitor(object):
    """
    monitors and reports on the status of uploads in progress

    Parameters:

        ``application``

            This is the next application in the WSGI stack.

        ``threshold``

            This is the size in bytes that is needed for the
            upload to be included in the monitor.

        ``timeout``

            This is the amount of time (in seconds) that a upload
            remains in the monitor after it has finished.

    Methods:

        ``uploads()``

            This returns a list of ``environ`` dict objects for each
            upload being currently monitored, or finished but whose time
            has not yet expired.

    For each request ``environ`` that is monitored, there are several
    variables that are stored:

        ``paste.bytes_received``

            This is the total number of bytes received for the given
            request; it can be compared with ``CONTENT_LENGTH`` to
            build a percentage complete.  This is an integer value.

        ``paste.request_started``

            This is the time (in seconds) when the request was started
            as obtained from ``time.time()``.  One would want to format
            this for presentation to the user, if necessary.

        ``paste.request_finished``

            This is the time (in seconds) when the request was finished,
            canceled, or otherwise disconnected.  This is None while
            the given upload is still in-progress.

    TODO: turn monitor into a queue and purge queue of finished
          requests that have passed the timeout period.
    """
    def __init__(self, application, threshold=None, timeout=None):
        self.application = application
        self.threshold = threshold or DEFAULT_THRESHOLD
        self.timeout   = timeout   or DEFAULT_TIMEOUT
        self.monitor   = []

    def __call__(self, environ, start_response):
        length = environ.get('CONTENT_LENGTH', 0)
        if length and int(length) > self.threshold:
            # replace input file object
            self.monitor.append(environ)
            environ[ENVIRON_RECEIVED] = 0
            environ[REQUEST_STARTED] = time.time()
            environ[REQUEST_FINISHED] = None
            environ['wsgi.input'] = \
                _ProgressFile(environ, environ['wsgi.input'])
            def finalizer(exc_info=None):
                environ[REQUEST_FINISHED] = time.time()
            return catch_errors(self.application, environ,
                       start_response, finalizer, finalizer)
        return self.application(environ, start_response)

    def uploads(self):
        return self.monitor

class UploadProgressReporter(object):
    """
    reports on the progress of uploads for a given user

    This reporter returns a JSON file (for use in AJAX) listing the
    uploads in progress for the given user.  By default, this reporter
    uses the ``REMOTE_USER`` environment to compare between the current
    request and uploads in-progress.  If they match, then a response
    record is formed.

        ``match()``

            This member function can be overriden to provide alternative
            matching criteria.  It takes two environments, the first
            is the current request, the second is a current upload.

        ``report()``

            This member function takes an environment and builds a
            ``dict`` that will be used to create a JSON mapping for
            the given upload.  By default, this just includes the
            percent complete and the request url.

    """
    def __init__(self, monitor):
        self.monitor   = monitor

    def match(self, search_environ, upload_environ):
        if search_environ.get('REMOTE_USER', None) == \
           upload_environ.get('REMOTE_USER', 0):
            return True
        return False

    def report(self, environ):
        retval = { 'started': time.strftime("%Y-%m-%d %H:%M:%S",
                                time.gmtime(environ[REQUEST_STARTED])),
                   'finished': '',
                   'content_length': environ.get('CONTENT_LENGTH'),
                   'bytes_received': environ[ENVIRON_RECEIVED],
                   'path_info': environ.get('PATH_INFO',''),
                   'query_string': environ.get('QUERY_STRING','')}
        finished = environ[REQUEST_FINISHED]
        if finished:
            retval['finished'] = time.strftime("%Y:%m:%d %H:%M:%S",
                                               time.gmtime(finished))
        return retval

    def __call__(self, environ, start_response):
        body = []
        for map in [self.report(env) for env in self.monitor.uploads()
                                             if self.match(environ, env)]:
            parts = []
            for k, v in map.items():
                v = str(v).replace("\\", "\\\\").replace('"', '\\"')
                parts.append('%s: "%s"' % (k, v))
            body.append("{ %s }" % ", ".join(parts))
        body = "[ %s ]" % ", ".join(body)
        start_response("200 OK", [('Content-Type', 'text/plain'),
                                  ('Content-Length', len(body))])
        return [body]

__all__ = ['UploadProgressMonitor', 'UploadProgressReporter']

if "__main__" == __name__:
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
