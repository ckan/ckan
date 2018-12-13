# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Middleware that profiles the request and displays profiling
information at the bottom of each page.
"""


import sys
import os
import hotshot
import hotshot.stats
import threading
import cgi
import time
from cStringIO import StringIO
from paste import response

__all__ = ['ProfileMiddleware', 'profile_decorator']

class ProfileMiddleware(object):

    """
    Middleware that profiles all requests.

    All HTML pages will have profiling information appended to them.
    The data is isolated to that single request, and does not include
    data from previous requests.

    This uses the ``hotshot`` module, which affects performance of the
    application.  It also runs in a single-threaded mode, so it is
    only usable in development environments.
    """

    style = ('clear: both; background-color: #ff9; color: #000; '
             'border: 2px solid #000; padding: 5px;')

    def __init__(self, app, global_conf=None,
                 log_filename='profile.log.tmp',
                 limit=40):
        self.app = app
        self.lock = threading.Lock()
        self.log_filename = log_filename
        self.limit = limit

    def __call__(self, environ, start_response):
        catch_response = []
        body = []
        def replace_start_response(status, headers, exc_info=None):
            catch_response.extend([status, headers])
            start_response(status, headers, exc_info)
            return body.append
        def run_app():
            app_iter = self.app(environ, replace_start_response)
            try:
                body.extend(app_iter)
            finally:
                if hasattr(app_iter, 'close'):
                    app_iter.close()
        self.lock.acquire()
        try:
            prof = hotshot.Profile(self.log_filename)
            prof.addinfo('URL', environ.get('PATH_INFO', ''))
            try:
                prof.runcall(run_app)
            finally:
                prof.close()
            body = ''.join(body)
            headers = catch_response[1]
            content_type = response.header_value(headers, 'content-type')
            if content_type is None or not content_type.startswith('text/html'):
                # We can't add info to non-HTML output
                return [body]
            stats = hotshot.stats.load(self.log_filename)
            stats.strip_dirs()
            stats.sort_stats('time', 'calls')
            output = capture_output(stats.print_stats, self.limit)
            output_callers = capture_output(
                stats.print_callers, self.limit)
            body += '<pre style="%s">%s\n%s</pre>' % (
                self.style, cgi.escape(output), cgi.escape(output_callers))
            return [body]
        finally:
            self.lock.release()

def capture_output(func, *args, **kw):
    # Not threadsafe! (that's okay when ProfileMiddleware uses it,
    # though, since it synchronizes itself.)
    out = StringIO()
    old_stdout = sys.stdout
    sys.stdout = out
    try:
        func(*args, **kw)
    finally:
        sys.stdout = old_stdout
    return out.getvalue()

def profile_decorator(**options):

    """
    Profile a single function call.
    
    Used around a function, like::

        @profile_decorator(options...)
        def ...

    All calls to the function will be profiled.  The options are
    all keywords, and are:

        log_file:
            The filename to log to (or ``'stdout'`` or ``'stderr'``).
            Default: stderr.
        display_limit:
            Only show the top N items, default: 20.
        sort_stats:
            A list of string-attributes to sort on.  Default
            ``('time', 'calls')``.
        strip_dirs:
            Strip directories/module names from files?  Default True.
        add_info:
            If given, this info will be added to the report (for your
            own tracking).  Default: none.
        log_filename:
            The temporary filename to log profiling data to.  Default;
            ``./profile_data.log.tmp``
        no_profile:
            If true, then don't actually profile anything.  Useful for
            conditional profiling.
    """

    if options.get('no_profile'):
        def decorator(func):
            return func
        return decorator
    def decorator(func):
        def replacement(*args, **kw):
            return DecoratedProfile(func, **options)(*args, **kw)
        return replacement
    return decorator

class DecoratedProfile(object):

    lock = threading.Lock()

    def __init__(self, func, **options):
        self.func = func
        self.options = options

    def __call__(self, *args, **kw):
        self.lock.acquire()
        try:
            return self.profile(self.func, *args, **kw)
        finally:
            self.lock.release()

    def profile(self, func, *args, **kw):
        ops = self.options
        prof_filename = ops.get('log_filename', 'profile_data.log.tmp')
        prof = hotshot.Profile(prof_filename)
        prof.addinfo('Function Call',
                     self.format_function(func, *args, **kw))
        if ops.get('add_info'):
            prof.addinfo('Extra info', ops['add_info'])
        exc_info = None
        try:
            start_time = time.time()
            try:
                result = prof.runcall(func, *args, **kw)
            except:
                exc_info = sys.exc_info()
            end_time = time.time()
        finally:
            prof.close()
        stats = hotshot.stats.load(prof_filename)
        os.unlink(prof_filename)
        if ops.get('strip_dirs', True):
            stats.strip_dirs()
        stats.sort_stats(*ops.get('sort_stats', ('time', 'calls')))
        display_limit = ops.get('display_limit', 20)
        output = capture_output(stats.print_stats, display_limit)
        output_callers = capture_output(
            stats.print_callers, display_limit)
        output_file = ops.get('log_file')
        if output_file in (None, 'stderr'):
            f = sys.stderr
        elif output_file in ('-', 'stdout'):
            f = sys.stdout
        else:
            f = open(output_file, 'a')
            f.write('\n%s\n' % ('-'*60))
            f.write('Date: %s\n' % time.strftime('%c'))
        f.write('Function call: %s\n'
                % self.format_function(func, *args, **kw))
        f.write('Wall time: %0.2f seconds\n'
                % (end_time - start_time))
        f.write(output)
        f.write(output_callers)
        if output_file not in (None, '-', 'stdout', 'stderr'):
            f.close()
        if exc_info:
            # We captured an exception earlier, now we re-raise it
            raise exc_info[0], exc_info[1], exc_info[2]
        return result
        
    def format_function(self, func, *args, **kw):
        args = map(repr, args)
        args.extend(
            ['%s=%r' % (k, v) for k, v in kw.items()])
        return '%s(%s)' % (func.__name__, ', '.join(args))
            
            
def make_profile_middleware(
    app, global_conf,
    log_filename='profile.log.tmp',
    limit=40):
    """
    Wrap the application in a component that will profile each
    request.  The profiling data is then appended to the output
    of each page.

    Note that this serializes all requests (i.e., removing
    concurrency).  Therefore never use this in production.
    """
    limit = int(limit)
    return ProfileMiddleware(
        app, log_filename=log_filename, limit=limit)
