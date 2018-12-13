# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# This code was written with funding by http://prometheusresearch.com
"""
WSGI HTTP Server

This is a minimalistic WSGI server using Python's built-in BaseHTTPServer;
if pyOpenSSL is installed, it also provides SSL capabilities.
"""

# @@: add in protection against HTTP/1.0 clients who claim to
#     be 1.1 but do not send a Content-Length

# @@: add support for chunked encoding, this is not a 1.1 server
#     till this is completed.

import atexit
import traceback
import socket, sys, threading, urlparse, Queue, urllib
import posixpath
import time
import thread
import os
from itertools import count
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn
from paste.util import converters
import logging
try:
    from paste.util import killthread
except ImportError:
    # Not available, probably no ctypes
    killthread = None

__all__ = ['WSGIHandlerMixin', 'WSGIServer', 'WSGIHandler', 'serve']
__version__ = "0.5"

class ContinueHook(object):
    """
    When a client request includes a 'Expect: 100-continue' header, then
    it is the responsibility of the server to send 100 Continue when it
    is ready for the content body.  This allows authentication, access
    levels, and other exceptions to be detected *before* bandwith is
    spent on the request body.

    This is a rfile wrapper that implements this functionality by
    sending 100 Continue to the client immediately after the user
    requests the content via a read() operation on the rfile stream.
    After this response is sent, it becomes a pass-through object.
    """

    def __init__(self, rfile, write):
        self._ContinueFile_rfile = rfile
        self._ContinueFile_write = write
        for attr in ('close', 'closed', 'fileno', 'flush',
                     'mode', 'bufsize', 'softspace'):
            if hasattr(rfile, attr):
                setattr(self, attr, getattr(rfile, attr))
        for attr in ('read', 'readline', 'readlines'):
            if hasattr(rfile, attr):
                setattr(self, attr, getattr(self, '_ContinueFile_' + attr))

    def _ContinueFile_send(self):
        self._ContinueFile_write("HTTP/1.1 100 Continue\r\n\r\n")
        rfile = self._ContinueFile_rfile
        for attr in ('read', 'readline', 'readlines'):
            if hasattr(rfile, attr):
                setattr(self, attr, getattr(rfile, attr))

    def _ContinueFile_read(self, size=-1):
        self._ContinueFile_send()
        return self._ContinueFile_rfile.read(size)

    def _ContinueFile_readline(self, size=-1):
        self._ContinueFile_send()
        return self._ContinueFile_rfile.readline(size)

    def _ContinueFile_readlines(self, sizehint=0):
        self._ContinueFile_send()
        return self._ContinueFile_rfile.readlines(sizehint)

class WSGIHandlerMixin:
    """
    WSGI mix-in for HTTPRequestHandler

    This class is a mix-in to provide WSGI functionality to any
    HTTPRequestHandler derivative (as provided in Python's BaseHTTPServer).
    This assumes a ``wsgi_application`` handler on ``self.server``.
    """
    lookup_addresses = True

    def log_request(self, *args, **kwargs):
        """ disable success request logging

        Logging transactions should not be part of a WSGI server,
        if you want logging; look at paste.translogger
        """
        pass

    def log_message(self, *args, **kwargs):
        """ disable error message logging

        Logging transactions should not be part of a WSGI server,
        if you want logging; look at paste.translogger
        """
        pass

    def version_string(self):
        """ behavior that BaseHTTPServer should have had """
        if not self.sys_version:
            return self.server_version
        else:
            return self.server_version + ' ' + self.sys_version

    def wsgi_write_chunk(self, chunk):
        """
        Write a chunk of the output stream; send headers if they
        have not already been sent.
        """
        if not self.wsgi_headers_sent and not self.wsgi_curr_headers:
            raise RuntimeError(
                "Content returned before start_response called")
        if not self.wsgi_headers_sent:
            self.wsgi_headers_sent = True
            (status, headers) = self.wsgi_curr_headers
            code, message = status.split(" ", 1)
            self.send_response(int(code), message)
            #
            # HTTP/1.1 compliance; either send Content-Length or
            # signal that the connection is being closed.
            #
            send_close = True
            for (k, v) in  headers:
                lk = k.lower()
                if 'content-length' == lk:
                    send_close = False
                if 'connection' == lk:
                    if 'close' == v.lower():
                        self.close_connection = 1
                        send_close = False
                self.send_header(k, v)
            if send_close:
                self.close_connection = 1
                self.send_header('Connection', 'close')

            self.end_headers()
        self.wfile.write(chunk)

    def wsgi_start_response(self, status, response_headers, exc_info=None):
        if exc_info:
            try:
                if self.wsgi_headers_sent:
                    raise exc_info[0], exc_info[1], exc_info[2]
                else:
                    # In this case, we're going to assume that the
                    # higher-level code is currently handling the
                    # issue and returning a resonable response.
                    # self.log_error(repr(exc_info))
                    pass
            finally:
                exc_info = None
        elif self.wsgi_curr_headers:
            assert 0, "Attempt to set headers a second time w/o an exc_info"
        self.wsgi_curr_headers = (status, response_headers)
        return self.wsgi_write_chunk

    def wsgi_setup(self, environ=None):
        """
        Setup the member variables used by this WSGI mixin, including
        the ``environ`` and status member variables.

        After the basic environment is created; the optional ``environ``
        argument can be used to override any settings.
        """

        (scheme, netloc, path, query, fragment) = urlparse.urlsplit(self.path)
        path = urllib.unquote(path)
        endslash = path.endswith('/')
        path = posixpath.normpath(path)
        if endslash and path != '/':
            # Put the slash back...
            path += '/'
        (server_name, server_port) = self.server.server_address[:2]

        rfile = self.rfile
        if 'HTTP/1.1' == self.protocol_version and \
                '100-continue' == self.headers.get('Expect','').lower():
            rfile = ContinueHook(rfile, self.wfile.write)
        else:
            # We can put in the protection to keep from over-reading the
            # file
            try:
                content_length = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                content_length = 0
            if not hasattr(self.connection, 'get_context'):
                # @@: LimitedLengthFile is currently broken in connection
                # with SSL (sporatic errors that are diffcult to trace, but
                # ones that go away when you don't use LimitedLengthFile)
                rfile = LimitedLengthFile(rfile, content_length)

        remote_address = self.client_address[0]
        self.wsgi_environ = {
                'wsgi.version': (1,0)
               ,'wsgi.url_scheme': 'http'
               ,'wsgi.input': rfile
               ,'wsgi.errors': sys.stderr
               ,'wsgi.multithread': True
               ,'wsgi.multiprocess': False
               ,'wsgi.run_once': False
               # CGI variables required by PEP-333
               ,'REQUEST_METHOD': self.command
               ,'SCRIPT_NAME': '' # application is root of server
               ,'PATH_INFO': path
               ,'QUERY_STRING': query
               ,'CONTENT_TYPE': self.headers.get('Content-Type', '')
               ,'CONTENT_LENGTH': self.headers.get('Content-Length', '0')
               ,'SERVER_NAME': server_name
               ,'SERVER_PORT': str(server_port)
               ,'SERVER_PROTOCOL': self.request_version
               # CGI not required by PEP-333
               ,'REMOTE_ADDR': remote_address
               }
        if scheme:
            self.wsgi_environ['paste.httpserver.proxy.scheme'] = scheme
        if netloc:
            self.wsgi_environ['paste.httpserver.proxy.host'] = netloc

        if self.lookup_addresses:
            # @@: make lookup_addreses actually work, at this point
            #     it has been address_string() is overriden down in
            #     file and hence is a noop
            if remote_address.startswith("192.168.") \
            or remote_address.startswith("10.") \
            or remote_address.startswith("172.16."):
                pass
            else:
                address_string = None # self.address_string()
                if address_string:
                    self.wsgi_environ['REMOTE_HOST'] = address_string

        if hasattr(self.server, 'thread_pool'):
            # Now that we know what the request was for, we should
            # tell the thread pool what its worker is working on
            self.server.thread_pool.worker_tracker[thread.get_ident()][1] = self.wsgi_environ
            self.wsgi_environ['paste.httpserver.thread_pool'] = self.server.thread_pool

        for k, v in self.headers.items():
            key = 'HTTP_' + k.replace("-","_").upper()
            if key in ('HTTP_CONTENT_TYPE','HTTP_CONTENT_LENGTH'):
                continue
            self.wsgi_environ[key] = ','.join(self.headers.getheaders(k))

        if hasattr(self.connection,'get_context'):
            self.wsgi_environ['wsgi.url_scheme'] = 'https'
            # @@: extract other SSL parameters from pyOpenSSL at...
            # http://www.modssl.org/docs/2.8/ssl_reference.html#ToC25

        if environ:
            assert isinstance(environ, dict)
            self.wsgi_environ.update(environ)
            if 'on' == environ.get('HTTPS'):
                self.wsgi_environ['wsgi.url_scheme'] = 'https'

        self.wsgi_curr_headers = None
        self.wsgi_headers_sent = False

    def wsgi_connection_drop(self, exce, environ=None):
        """
        Override this if you're interested in socket exceptions, such
        as when the user clicks 'Cancel' during a file download.
        """
        pass

    def wsgi_execute(self, environ=None):
        """
        Invoke the server's ``wsgi_application``.
        """

        self.wsgi_setup(environ)

        try:
            result = self.server.wsgi_application(self.wsgi_environ,
                                                  self.wsgi_start_response)
            try:
                for chunk in result:
                    self.wsgi_write_chunk(chunk)
                if not self.wsgi_headers_sent:
                    self.wsgi_write_chunk('')
            finally:
                if hasattr(result,'close'):
                    result.close()
                result = None
        except socket.error, exce:
            self.wsgi_connection_drop(exce, environ)
            return
        except:
            if not self.wsgi_headers_sent:
                error_msg = "Internal Server Error\n"
                self.wsgi_curr_headers = (
                    '500 Internal Server Error',
                    [('Content-type', 'text/plain'),
                     ('Content-length', str(len(error_msg)))])
                self.wsgi_write_chunk("Internal Server Error\n")
            raise

#
# SSL Functionality
#
# This implementation was motivated by Sebastien Martini's SSL example
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/442473
#
try:
    from OpenSSL import SSL, tsafe
    SocketErrors = (socket.error, SSL.ZeroReturnError, SSL.SysCallError)
except ImportError:
    # Do not require pyOpenSSL to be installed, but disable SSL
    # functionality in that case.
    SSL = None
    SocketErrors = (socket.error,)
    class SecureHTTPServer(HTTPServer):
        def __init__(self, server_address, RequestHandlerClass,
                     ssl_context=None, request_queue_size=None):
            assert not ssl_context, "pyOpenSSL not installed"
            HTTPServer.__init__(self, server_address, RequestHandlerClass)
            if request_queue_size:
                self.socket.listen(request_queue_size)
else:

    class _ConnFixer(object):
        """ wraps a socket connection so it implements makefile """
        def __init__(self, conn):
            self.__conn = conn
        def makefile(self, mode, bufsize):
            return socket._fileobject(self.__conn, mode, bufsize)
        def __getattr__(self, attrib):
            return getattr(self.__conn, attrib)

    class SecureHTTPServer(HTTPServer):
        """
        Provides SSL server functionality on top of the BaseHTTPServer
        by overriding _private_ members of Python's standard
        distribution. The interface for this instance only changes by
        adding a an optional ssl_context attribute to the constructor:

              cntx = SSL.Context(SSL.SSLv23_METHOD)
              cntx.use_privatekey_file("host.pem")
              cntx.use_certificate_file("host.pem")

        """

        def __init__(self, server_address, RequestHandlerClass,
                     ssl_context=None, request_queue_size=None):
            # This overrides the implementation of __init__ in python's
            # SocketServer.TCPServer (which BaseHTTPServer.HTTPServer
            # does not override, thankfully).
            HTTPServer.__init__(self, server_address, RequestHandlerClass)
            self.socket = socket.socket(self.address_family,
                                        self.socket_type)
            self.ssl_context = ssl_context
            if ssl_context:
                class TSafeConnection(tsafe.Connection):
                    def settimeout(self, *args):
                        self._lock.acquire()
                        try:
                            return self._ssl_conn.settimeout(*args)
                        finally:
                            self._lock.release()
                    def gettimeout(self):
                        self._lock.acquire()
                        try:
                            return self._ssl_conn.gettimeout()
                        finally:
                            self._lock.release()
                self.socket = TSafeConnection(ssl_context, self.socket)
            self.server_bind()
            if request_queue_size:
                self.socket.listen(request_queue_size)
            self.server_activate()

        def get_request(self):
            # The default SSL request object does not seem to have a
            # ``makefile(mode, bufsize)`` method as expected by
            # Socketserver.StreamRequestHandler.
            (conn, info) = self.socket.accept()
            if self.ssl_context:
                conn = _ConnFixer(conn)
            return (conn, info)

    def _auto_ssl_context():
        import OpenSSL, time, random
        pkey = OpenSSL.crypto.PKey()
        pkey.generate_key(OpenSSL.crypto.TYPE_RSA, 768)

        cert = OpenSSL.crypto.X509()

        cert.set_serial_number(random.randint(0, sys.maxint))
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(60 * 60 * 24 * 365)
        cert.get_subject().CN = '*'
        cert.get_subject().O = 'Dummy Certificate'
        cert.get_issuer().CN = 'Untrusted Authority'
        cert.get_issuer().O = 'Self-Signed'
        cert.set_pubkey(pkey)
        cert.sign(pkey, 'md5')

        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.use_privatekey(pkey)
        ctx.use_certificate(cert)

        return ctx

class WSGIHandler(WSGIHandlerMixin, BaseHTTPRequestHandler):
    """
    A WSGI handler that overrides POST, GET and HEAD to delegate
    requests to the server's ``wsgi_application``.
    """
    server_version = 'PasteWSGIServer/' + __version__

    def handle_one_request(self):
        """Handle a single HTTP request.

        You normally don't need to override this method; see the class
        __doc__ string for information on how to handle specific HTTP
        commands such as GET and POST.

        """
        self.raw_requestline = self.rfile.readline()
        if not self.raw_requestline:
            self.close_connection = 1
            return
        if not self.parse_request(): # An error code has been sent, just exit
            return
        self.wsgi_execute()

    def handle(self):
        # don't bother logging disconnects while handling a request
        try:
            BaseHTTPRequestHandler.handle(self)
        except SocketErrors, exce:
            self.wsgi_connection_drop(exce)

    def address_string(self):
        """Return the client address formatted for logging.

        This is overridden so that no hostname lookup is done.
        """
        return ''

class LimitedLengthFile(object):
    def __init__(self, file, length):
        self.file = file
        self.length = length
        self._consumed = 0
        if hasattr(self.file, 'seek'):
            self.seek = self._seek

    def __repr__(self):
        base_repr = repr(self.file)
        return base_repr[:-1] + ' length=%s>' % self.length

    def read(self, length=None):
        left = self.length - self._consumed
        if length is None:
            length = left
        else:
            length = min(length, left)
        # next two lines are hnecessary only if read(0) blocks
        if not left:
            return ''
        data = self.file.read(length)
        self._consumed += len(data)
        return data

    def readline(self, *args):
        max_read = self.length - self._consumed
        if len(args):
            max_read = min(args[0], max_read)
        data = self.file.readline(max_read)
        self._consumed += len(data)
        return data

    def readlines(self, hint=None):
        data = self.file.readlines(hint)
        for chunk in data:
            self._consumed += len(chunk)
        return data

    def __iter__(self):
        return self

    def next(self):
        if self.length - self._consumed <= 0:
            raise StopIteration
        return self.readline()

    ## Optional methods ##

    def _seek(self, place):
        self.file.seek(place)
        self._consumed = place

    def tell(self):
        if hasattr(self.file, 'tell'):
            return self.file.tell()
        else:
            return self._consumed

class ThreadPool(object):
    """
    Generic thread pool with a queue of callables to consume.

    Keeps a notion of the status of its worker threads:

    idle: worker thread with nothing to do

    busy: worker thread doing its job

    hung: worker thread that's been doing a job for too long

    dying: a hung thread that has been killed, but hasn't died quite
    yet.

    zombie: what was a worker thread that we've tried to kill but
    isn't dead yet.

    At any time you can call track_threads, to get a dictionary with
    these keys and lists of thread_ids that fall in that status.  All
    keys will be present, even if they point to emty lists.

    hung threads are threads that have been busy more than
    hung_thread_limit seconds.  Hung threads are killed when they live
    longer than kill_thread_limit seconds.  A thread is then
    considered dying for dying_limit seconds, if it is still alive
    after that it is considered a zombie.

    When there are no idle workers and a request comes in, another
    worker *may* be spawned.  If there are less than spawn_if_under
    threads in the busy state, another thread will be spawned.  So if
    the limit is 5, and there are 4 hung threads and 6 busy threads,
    no thread will be spawned.

    When there are more than max_zombie_threads_before_die zombie
    threads, a SystemExit exception will be raised, stopping the
    server.  Use 0 or None to never raise this exception.  Zombie
    threads *should* get cleaned up, but killing threads is no
    necessarily reliable.  This is turned off by default, since it is
    only a good idea if you've deployed the server with some process
    watching from above (something similar to daemontools or zdaemon).

    Each worker thread only processes ``max_requests`` tasks before it
    dies and replaces itself with a new worker thread.
    """


    SHUTDOWN = object()

    def __init__(
        self, nworkers, name="ThreadPool", daemon=False,
        max_requests=100, # threads are killed after this many requests
        hung_thread_limit=30, # when a thread is marked "hung"
        kill_thread_limit=1800, # when you kill that hung thread
        dying_limit=300, # seconds that a kill should take to go into effect (longer than this and the thread is a "zombie")
        spawn_if_under=5, # spawn if there's too many hung threads
        max_zombie_threads_before_die=0, # when to give up on the process
        hung_check_period=100, # every 100 requests check for hung workers
        logger=None, # Place to log messages to
        error_email=None, # Person(s) to notify if serious problem occurs
        ):
        """
        Create thread pool with `nworkers` worker threads.
        """
        self.nworkers = nworkers
        self.max_requests = max_requests
        self.name = name
        self.queue = Queue.Queue()
        self.workers = []
        self.daemon = daemon
        if logger is None:
            logger = logging.getLogger('paste.httpserver.ThreadPool')
        if isinstance(logger, basestring):
            logger = logging.getLogger(logger)
        self.logger = logger
        self.error_email = error_email
        self._worker_count = count()

        assert (not kill_thread_limit
                or kill_thread_limit >= hung_thread_limit), (
            "kill_thread_limit (%s) should be higher than hung_thread_limit (%s)"
            % (kill_thread_limit, hung_thread_limit))
        if not killthread:
            kill_thread_limit = 0
            self.logger.info(
                "Cannot use kill_thread_limit as ctypes/killthread is not available")
        self.kill_thread_limit = kill_thread_limit
        self.dying_limit = dying_limit
        self.hung_thread_limit = hung_thread_limit
        assert spawn_if_under <= nworkers, (
            "spawn_if_under (%s) should be less than nworkers (%s)"
            % (spawn_if_under, nworkers))
        self.spawn_if_under = spawn_if_under
        self.max_zombie_threads_before_die = max_zombie_threads_before_die
        self.hung_check_period = hung_check_period
        self.requests_since_last_hung_check = 0
        # Used to keep track of what worker is doing what:
        self.worker_tracker = {}
        # Used to keep track of the workers not doing anything:
        self.idle_workers = []
        # Used to keep track of threads that have been killed, but maybe aren't dead yet:
        self.dying_threads = {}
        # This is used to track when we last had to add idle workers;
        # we shouldn't cull extra workers until some time has passed
        # (hung_thread_limit) since workers were added:
        self._last_added_new_idle_workers = 0
        if not daemon:
            atexit.register(self.shutdown)
        for i in range(self.nworkers):
            self.add_worker_thread(message='Initial worker pool')

    def add_task(self, task):
        """
        Add a task to the queue
        """
        self.logger.debug('Added task (%i tasks queued)', self.queue.qsize())
        if self.hung_check_period:
            self.requests_since_last_hung_check += 1
            if self.requests_since_last_hung_check > self.hung_check_period:
                self.requests_since_last_hung_check = 0
                self.kill_hung_threads()
        if not self.idle_workers and self.spawn_if_under:
            # spawn_if_under can come into effect...
            busy = 0
            now = time.time()
            self.logger.debug('No idle workers for task; checking if we need to make more workers')
            for worker in self.workers:
                if not hasattr(worker, 'thread_id'):
                    # Not initialized
                    continue
                time_started, info = self.worker_tracker.get(worker.thread_id,
                                                             (None, None))
                if time_started is not None:
                    if now - time_started < self.hung_thread_limit:
                        busy += 1
            if busy < self.spawn_if_under:
                self.logger.info(
                    'No idle tasks, and only %s busy tasks; adding %s more '
                    'workers', busy, self.spawn_if_under-busy)
                self._last_added_new_idle_workers = time.time()
                for i in range(self.spawn_if_under - busy):
                    self.add_worker_thread(message='Response to lack of idle workers')
            else:
                self.logger.debug(
                    'No extra workers needed (%s busy workers)',
                    busy)
        if (len(self.workers) > self.nworkers
            and len(self.idle_workers) > 3
            and time.time()-self._last_added_new_idle_workers > self.hung_thread_limit):
            # We've spawned worers in the past, but they aren't needed
            # anymore; kill off some
            self.logger.info(
                'Culling %s extra workers (%s idle workers present)',
                len(self.workers)-self.nworkers, len(self.idle_workers))
            self.logger.debug(
                'Idle workers: %s', self.idle_workers)
            for i in range(len(self.workers) - self.nworkers):
                self.queue.put(self.SHUTDOWN)
        self.queue.put(task)

    def track_threads(self):
        """
        Return a dict summarizing the threads in the pool (as
        described in the ThreadPool docstring).
        """
        result = dict(idle=[], busy=[], hung=[], dying=[], zombie=[])
        now = time.time()
        for worker in self.workers:
            if not hasattr(worker, 'thread_id'):
                # The worker hasn't fully started up, we should just
                # ignore it
                continue
            time_started, info = self.worker_tracker.get(worker.thread_id,
                                                         (None, None))
            if time_started is not None:
                if now - time_started > self.hung_thread_limit:
                    result['hung'].append(worker)
                else:
                    result['busy'].append(worker)
            else:
                result['idle'].append(worker)
        for thread_id, (time_killed, worker) in self.dying_threads.items():
            if not self.thread_exists(thread_id):
                # Cull dying threads that are actually dead and gone
                self.logger.info('Killed thread %s no longer around',
                                 thread_id)
                try:
                    del self.dying_threads[thread_id]
                except KeyError:
                    pass
                continue
            if now - time_killed > self.dying_limit:
                result['zombie'].append(worker)
            else:
                result['dying'].append(worker)
        return result

    def kill_worker(self, thread_id):
        """
        Removes the worker with the given thread_id from the pool, and
        replaces it with a new worker thread.

        This should only be done for mis-behaving workers.
        """
        if killthread is None:
            raise RuntimeError(
                "Cannot kill worker; killthread/ctypes not available")
        thread_obj = threading._active.get(thread_id)
        killthread.async_raise(thread_id, SystemExit)
        try:
            del self.worker_tracker[thread_id]
        except KeyError:
            pass
        self.logger.info('Killing thread %s', thread_id)
        if thread_obj in self.workers:
            self.workers.remove(thread_obj)
        self.dying_threads[thread_id] = (time.time(), thread_obj)
        self.add_worker_thread(message='Replacement for killed thread %s' % thread_id)

    def thread_exists(self, thread_id):
        """
        Returns true if a thread with this id is still running
        """
        return thread_id in threading._active

    def add_worker_thread(self, *args, **kwargs):
        index = self._worker_count.next()
        worker = threading.Thread(target=self.worker_thread_callback,
                                  args=args, kwargs=kwargs,
                                  name=("worker %d" % index))
        worker.setDaemon(self.daemon)
        worker.start()

    def kill_hung_threads(self):
        """
        Tries to kill any hung threads
        """
        if not self.kill_thread_limit:
            # No killing should occur
            return
        now = time.time()
        max_time = 0
        total_time = 0
        idle_workers = 0
        starting_workers = 0
        working_workers = 0
        killed_workers = 0
        for worker in self.workers:
            if not hasattr(worker, 'thread_id'):
                # Not setup yet
                starting_workers += 1
                continue
            time_started, info = self.worker_tracker.get(worker.thread_id,
                                                         (None, None))
            if time_started is None:
                # Must be idle
                idle_workers += 1
                continue
            working_workers += 1
            max_time = max(max_time, now-time_started)
            total_time += now-time_started
            if now - time_started > self.kill_thread_limit:
                self.logger.warning(
                    'Thread %s hung (working on task for %i seconds)',
                    worker.thread_id, now - time_started)
                try:
                    import pprint
                    info_desc = pprint.pformat(info)
                except:
                    out = StringIO()
                    traceback.print_exc(file=out)
                    info_desc = 'Error:\n%s' % out.getvalue()
                self.notify_problem(
                    "Killing worker thread (id=%(thread_id)s) because it has been \n"
                    "working on task for %(time)s seconds (limit is %(limit)s)\n"
                    "Info on task:\n"
                    "%(info)s"
                    % dict(thread_id=worker.thread_id,
                           time=now - time_started,
                           limit=self.kill_thread_limit,
                           info=info_desc))
                self.kill_worker(worker.thread_id)
                killed_workers += 1
        if working_workers:
            ave_time = float(total_time) / working_workers
            ave_time = '%.2fsec' % ave_time
        else:
            ave_time = 'N/A'
        self.logger.info(
            "kill_hung_threads status: %s threads (%s working, %s idle, %s starting) "
            "ave time %s, max time %.2fsec, killed %s workers"
            % (idle_workers + starting_workers + working_workers,
               working_workers, idle_workers, starting_workers,
               ave_time, max_time, killed_workers))
        self.check_max_zombies()

    def check_max_zombies(self):
        """
        Check if we've reached max_zombie_threads_before_die; if so
        then kill the entire process.
        """
        if not self.max_zombie_threads_before_die:
            return
        found = []
        now = time.time()
        for thread_id, (time_killed, worker) in self.dying_threads.items():
            if not self.thread_exists(thread_id):
                # Cull dying threads that are actually dead and gone
                try:
                    del self.dying_threads[thread_id]
                except KeyError:
                    pass
                continue
            if now - time_killed > self.dying_limit:
                found.append(thread_id)
        if found:
            self.logger.info('Found %s zombie threads', found)
        if len(found) > self.max_zombie_threads_before_die:
            self.logger.fatal(
                'Exiting process because %s zombie threads is more than %s limit',
                len(found), self.max_zombie_threads_before_die)
            self.notify_problem(
                "Exiting process because %(found)s zombie threads "
                "(more than limit of %(limit)s)\n"
                "Bad threads (ids):\n"
                "  %(ids)s\n"
                % dict(found=len(found),
                       limit=self.max_zombie_threads_before_die,
                       ids="\n  ".join(map(str, found))),
                subject="Process restart (too many zombie threads)")
            self.shutdown(10)
            print 'Shutting down', threading.currentThread()
            raise ServerExit(3)

    def worker_thread_callback(self, message=None):
        """
        Worker thread should call this method to get and process queued
        callables.
        """
        thread_obj = threading.currentThread()
        thread_id = thread_obj.thread_id = thread.get_ident()
        self.workers.append(thread_obj)
        self.idle_workers.append(thread_id)
        requests_processed = 0
        add_replacement_worker = False
        self.logger.debug('Started new worker %s: %s', thread_id, message)
        try:
            while True:
                if self.max_requests and self.max_requests < requests_processed:
                    # Replace this thread then die
                    self.logger.debug('Thread %s processed %i requests (limit %s); stopping thread'
                                      % (thread_id, requests_processed, self.max_requests))
                    add_replacement_worker = True
                    break
                runnable = self.queue.get()
                if runnable is ThreadPool.SHUTDOWN:
                    self.logger.debug('Worker %s asked to SHUTDOWN', thread_id)
                    break
                try:
                    self.idle_workers.remove(thread_id)
                except ValueError:
                    pass
                self.worker_tracker[thread_id] = [time.time(), None]
                requests_processed += 1
                try:
                    try:
                        runnable()
                    except:
                        # We are later going to call sys.exc_clear(),
                        # removing all remnants of any exception, so
                        # we should log it now.  But ideally no
                        # exception should reach this level
                        print >> sys.stderr, (
                            'Unexpected exception in worker %r' % runnable)
                        traceback.print_exc()
                    if thread_id in self.dying_threads:
                        # That last exception was intended to kill me
                        break
                finally:
                    try:
                        del self.worker_tracker[thread_id]
                    except KeyError:
                        pass
                    sys.exc_clear()
                self.idle_workers.append(thread_id)
        finally:
            try:
                del self.worker_tracker[thread_id]
            except KeyError:
                pass
            try:
                self.idle_workers.remove(thread_id)
            except ValueError:
                pass
            try:
                self.workers.remove(thread_obj)
            except ValueError:
                pass
            try:
                del self.dying_threads[thread_id]
            except KeyError:
                pass
            if add_replacement_worker:
                self.add_worker_thread(message='Voluntary replacement for thread %s' % thread_id)

    def shutdown(self, force_quit_timeout=0):
        """
        Shutdown the queue (after finishing any pending requests).
        """
        self.logger.info('Shutting down threadpool')
        # Add a shutdown request for every worker
        for i in range(len(self.workers)):
            self.queue.put(ThreadPool.SHUTDOWN)
        # Wait for each thread to terminate
        hung_workers = []
        for worker in self.workers:
            worker.join(0.5)
            if worker.isAlive():
                hung_workers.append(worker)
        zombies = []
        for thread_id in self.dying_threads:
            if self.thread_exists(thread_id):
                zombies.append(thread_id)
        if hung_workers or zombies:
            self.logger.info("%s workers didn't stop properly, and %s zombies",
                             len(hung_workers), len(zombies))
            if hung_workers:
                for worker in hung_workers:
                    self.kill_worker(worker.thread_id)
                self.logger.info('Workers killed forcefully')
            if force_quit_timeout:
                hung = []
                timed_out = False
                need_force_quit = bool(zombies)
                for workers in self.workers:
                    if not timed_out and worker.isAlive():
                        timed_out = True
                        worker.join(force_quit_timeout)
                    if worker.isAlive():
                        print "Worker %s won't die" % worker
                        need_force_quit = True
                if need_force_quit:
                    import atexit
                    # Remove the threading atexit callback
                    for callback in list(atexit._exithandlers):
                        func = getattr(callback[0], 'im_func', None)
                        if not func:
                            continue
                        globs = getattr(func, 'func_globals', {})
                        mod = globs.get('__name__')
                        if mod == 'threading':
                            atexit._exithandlers.remove(callback)
                    atexit._run_exitfuncs()
                    print 'Forcefully exiting process'
                    os._exit(3)
                else:
                    self.logger.info('All workers eventually killed')
        else:
            self.logger.info('All workers stopped')

    def notify_problem(self, msg, subject=None, spawn_thread=True):
        """
        Called when there's a substantial problem.  msg contains the
        body of the notification, subject the summary.

        If spawn_thread is true, then the email will be send in
        another thread (so this doesn't block).
        """
        if not self.error_email:
            return
        if spawn_thread:
            t = threading.Thread(
                target=self.notify_problem,
                args=(msg, subject, False))
            t.start()
            return
        from_address = 'errors@localhost'
        if not subject:
            subject = msg.strip().splitlines()[0]
            subject = subject[:50]
            subject = '[http threadpool] %s' % subject
        headers = [
            "To: %s" % self.error_email,
            "From: %s" % from_address,
            "Subject: %s" % subject,
            ]
        try:
            system = ' '.join(os.uname())
        except:
            system = '(unknown)'
        body = (
            "An error has occurred in the paste.httpserver.ThreadPool\n"
            "Error:\n"
            "  %(msg)s\n"
            "Occurred at: %(time)s\n"
            "PID: %(pid)s\n"
            "System: %(system)s\n"
            "Server .py file: %(file)s\n"
            % dict(msg=msg,
                   time=time.strftime("%c"),
                   pid=os.getpid(),
                   system=system,
                   file=os.path.abspath(__file__),
                   ))
        message = '\n'.join(headers) + "\n\n" + body
        import smtplib
        server = smtplib.SMTP('localhost')
        error_emails = [
            e.strip() for e in self.error_email.split(",")
            if e.strip()]
        server.sendmail(from_address, error_emails, message)
        server.quit()
        print 'email sent to', error_emails, message

class ThreadPoolMixIn(object):
    """
    Mix-in class to process requests from a thread pool
    """
    def __init__(self, nworkers, daemon=False, **threadpool_options):
        # Create and start the workers
        self.running = True
        assert nworkers > 0, "ThreadPoolMixIn servers must have at least one worker"
        self.thread_pool = ThreadPool(
            nworkers,
            "ThreadPoolMixIn HTTP server on %s:%d"
            % (self.server_name, self.server_port),
            daemon,
            **threadpool_options)

    def process_request(self, request, client_address):
        """
        Queue the request to be processed by on of the thread pool threads
        """
        # This sets the socket to blocking mode (and no timeout) since it
        # may take the thread pool a little while to get back to it. (This
        # is the default but since we set a timeout on the parent socket so
        # that we can trap interrupts we need to restore this,.)
        request.setblocking(1)
        # Queue processing of the request
        self.thread_pool.add_task(
             lambda: self.process_request_in_thread(request, client_address))

    def handle_error(self, request, client_address):
        exc_class, exc, tb = sys.exc_info()
        if exc_class is ServerExit:
            # This is actually a request to stop the server
            raise
        return super(ThreadPoolMixIn, self).handle_error(request, client_address)

    def process_request_in_thread(self, request, client_address):
        """
        The worker thread should call back here to do the rest of the
        request processing. Error handling normaller done in 'handle_request'
        must be done here.
        """
        try:
            self.finish_request(request, client_address)
            self.close_request(request)
        except:
            self.handle_error(request, client_address)
            self.close_request(request)
            exc = sys.exc_info()[1]
            if isinstance(exc, (MemoryError, KeyboardInterrupt)):
                raise

    def serve_forever(self):
        """
        Overrides `serve_forever` to shut the threadpool down cleanly.
        """
        try:
            while self.running:
                try:
                    self.handle_request()
                except socket.timeout:
                    # Timeout is expected, gives interrupts a chance to
                    # propogate, just keep handling
                    pass
        finally:
            self.thread_pool.shutdown()

    def server_activate(self):
        """
        Overrides server_activate to set timeout on our listener socket.
        """
        # We set the timeout here so that we can trap interrupts on windows
        self.socket.settimeout(1)

    def server_close(self):
        """
        Finish pending requests and shutdown the server.
        """
        self.running = False
        self.socket.close()
        self.thread_pool.shutdown(60)

class WSGIServerBase(SecureHTTPServer):
    def __init__(self, wsgi_application, server_address,
                 RequestHandlerClass=None, ssl_context=None,
                 request_queue_size=None):
        SecureHTTPServer.__init__(self, server_address,
                                  RequestHandlerClass, ssl_context,
                                  request_queue_size=request_queue_size)
        self.wsgi_application = wsgi_application
        self.wsgi_socket_timeout = None

    def get_request(self):
        # If there is a socket_timeout, set it on the accepted
        (conn,info) = SecureHTTPServer.get_request(self)
        if self.wsgi_socket_timeout:
            conn.settimeout(self.wsgi_socket_timeout)
        return (conn, info)

class WSGIServer(ThreadingMixIn, WSGIServerBase):
    daemon_threads = False

class WSGIThreadPoolServer(ThreadPoolMixIn, WSGIServerBase):
    def __init__(self, wsgi_application, server_address,
                 RequestHandlerClass=None, ssl_context=None,
                 nworkers=10, daemon_threads=False,
                 threadpool_options=None, request_queue_size=None):
        WSGIServerBase.__init__(self, wsgi_application, server_address,
                                RequestHandlerClass, ssl_context,
                                request_queue_size=request_queue_size)
        if threadpool_options is None:
            threadpool_options = {}
        ThreadPoolMixIn.__init__(self, nworkers, daemon_threads,
                                 **threadpool_options)

class ServerExit(SystemExit):
    """
    Raised to tell the server to really exit (SystemExit is normally
    caught)
    """

def serve(application, host=None, port=None, handler=None, ssl_pem=None,
          ssl_context=None, server_version=None, protocol_version=None,
          start_loop=True, daemon_threads=None, socket_timeout=None,
          use_threadpool=None, threadpool_workers=10,
          threadpool_options=None, request_queue_size=5):
    """
    Serves your ``application`` over HTTP(S) via WSGI interface

    ``host``

        This is the ipaddress to bind to (or a hostname if your
        nameserver is properly configured).  This defaults to
        127.0.0.1, which is not a public interface.

    ``port``

        The port to run on, defaults to 8080 for HTTP, or 4443 for
        HTTPS. This can be a string or an integer value.

    ``handler``

        This is the HTTP request handler to use, it defaults to
        ``WSGIHandler`` in this module.

    ``ssl_pem``

        This an optional SSL certificate file (via OpenSSL). You can
        supply ``*`` and a development-only certificate will be
        created for you, or you can generate a self-signed test PEM
        certificate file as follows::

            $ openssl genrsa 1024 > host.key
            $ chmod 400 host.key
            $ openssl req -new -x509 -nodes -sha1 -days 365  \\
                          -key host.key > host.cert
            $ cat host.cert host.key > host.pem
            $ chmod 400 host.pem

    ``ssl_context``

        This an optional SSL context object for the server.  A SSL
        context will be automatically constructed for you if you supply
        ``ssl_pem``.  Supply this to use a context of your own
        construction.

    ``server_version``

        The version of the server as reported in HTTP response line. This
        defaults to something like "PasteWSGIServer/0.5".  Many servers
        hide their code-base identity with a name like 'Amnesiac/1.0'

    ``protocol_version``

        This sets the protocol used by the server, by default
        ``HTTP/1.0``. There is some support for ``HTTP/1.1``, which
        defaults to nicer keep-alive connections.  This server supports
        ``100 Continue``, but does not yet support HTTP/1.1 Chunked
        Encoding. Hence, if you use HTTP/1.1, you're somewhat in error
        since chunked coding is a mandatory requirement of a HTTP/1.1
        server.  If you specify HTTP/1.1, every response *must* have a
        ``Content-Length`` and you must be careful not to read past the
        end of the socket.

    ``start_loop``

        This specifies if the server loop (aka ``server.serve_forever()``)
        should be called; it defaults to ``True``.

    ``daemon_threads``

        This flag specifies if when your webserver terminates all
        in-progress client connections should be droppped.  It defaults
        to ``False``.   You might want to set this to ``True`` if you
        are using ``HTTP/1.1`` and don't set a ``socket_timeout``.

    ``socket_timeout``

        This specifies the maximum amount of time that a connection to a
        given client will be kept open.  At this time, it is a rude
        disconnect, but at a later time it might follow the RFC a bit
        more closely.

    ``use_threadpool``

        Server requests from a pool of worker threads (``threadpool_workers``)
        rather than creating a new thread for each request. This can
        substantially reduce latency since there is a high cost associated
        with thread creation.

    ``threadpool_workers``

        Number of worker threads to create when ``use_threadpool`` is true. This
        can be a string or an integer value.

    ``threadpool_options``

        A dictionary of options to be used when instantiating the
        threadpool.  See paste.httpserver.ThreadPool for specific
        options (``threadpool_workers`` is a specific option that can
        also go here).

    ``request_queue_size``

        The 'backlog' argument to socket.listen(); specifies the
        maximum number of queued connections.

    """
    is_ssl = False
    if ssl_pem or ssl_context:
        assert SSL, "pyOpenSSL is not installed"
        is_ssl = True
        port = int(port or 4443)
        if not ssl_context:
            if ssl_pem == '*':
                ssl_context = _auto_ssl_context()
            else:
                ssl_context = SSL.Context(SSL.SSLv23_METHOD)
                ssl_context.use_privatekey_file(ssl_pem)
                ssl_context.use_certificate_chain_file(ssl_pem)

    host = host or '127.0.0.1'
    if port is None:
        if ':' in host:
            host, port = host.split(':', 1)
        else:
            port = 8080
    server_address = (host, int(port))

    if not handler:
        handler = WSGIHandler
    if server_version:
        handler.server_version = server_version
        handler.sys_version = None
    if protocol_version:
        assert protocol_version in ('HTTP/0.9', 'HTTP/1.0', 'HTTP/1.1')
        handler.protocol_version = protocol_version

    if use_threadpool is None:
        use_threadpool = True

    if converters.asbool(use_threadpool):
        server = WSGIThreadPoolServer(application, server_address, handler,
                                      ssl_context, int(threadpool_workers),
                                      daemon_threads,
                                      threadpool_options=threadpool_options,
                                      request_queue_size=request_queue_size)
    else:
        server = WSGIServer(application, server_address, handler, ssl_context,
                            request_queue_size=request_queue_size)
        if daemon_threads:
            server.daemon_threads = daemon_threads

    if socket_timeout:
        server.wsgi_socket_timeout = int(socket_timeout)

    if converters.asbool(start_loop):
        protocol = is_ssl and 'https' or 'http'
        host, port = server.server_address[:2]
        if host == '0.0.0.0':
            print 'serving on 0.0.0.0:%s view at %s://127.0.0.1:%s' % \
                (port, protocol, port)
        else:
            print "serving on %s://%s:%s" % (protocol, host, port)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            # allow CTRL+C to shutdown
            pass
    return server

# For paste.deploy server instantiation (egg:Paste#http)
# Note: this gets a separate function because it has to expect string
# arguments (though that's not much of an issue yet, ever?)
def server_runner(wsgi_app, global_conf, **kwargs):
    from paste.deploy.converters import asbool
    for name in ['port', 'socket_timeout', 'threadpool_workers',
                 'threadpool_hung_thread_limit',
                 'threadpool_kill_thread_limit',
                 'threadpool_dying_limit', 'threadpool_spawn_if_under',
                 'threadpool_max_zombie_threads_before_die',
                 'threadpool_hung_check_period',
                 'threadpool_max_requests', 'request_queue_size']:
        if name in kwargs:
            kwargs[name] = int(kwargs[name])
    for name in ['use_threadpool', 'daemon_threads']:
        if name in kwargs:
            kwargs[name] = asbool(kwargs[name])
    threadpool_options = {}
    for name, value in kwargs.items():
        if name.startswith('threadpool_') and name != 'threadpool_workers':
            threadpool_options[name[len('threadpool_'):]] = value
            del kwargs[name]
    if ('error_email' not in threadpool_options
        and 'error_email' in global_conf):
        threadpool_options['error_email'] = global_conf['error_email']
    kwargs['threadpool_options'] = threadpool_options
    serve(wsgi_app, **kwargs)

server_runner.__doc__ = (serve.__doc__ or '') + """

    You can also set these threadpool options:

    ``threadpool_max_requests``:

        The maximum number of requests a worker thread will process
        before dying (and replacing itself with a new worker thread).
        Default 100.

    ``threadpool_hung_thread_limit``:

        The number of seconds a thread can work on a task before it is
        considered hung (stuck).  Default 30 seconds.

    ``threadpool_kill_thread_limit``:

        The number of seconds a thread can work before you should kill it
        (assuming it will never finish).  Default 600 seconds (10 minutes).

    ``threadpool_dying_limit``:

        The length of time after killing a thread that it should actually
        disappear.  If it lives longer than this, it is considered a
        "zombie".  Note that even in easy situations killing a thread can
        be very slow.  Default 300 seconds (5 minutes).

    ``threadpool_spawn_if_under``:

        If there are no idle threads and a request comes in, and there are
        less than this number of *busy* threads, then add workers to the
        pool.  Busy threads are threads that have taken less than
        ``threadpool_hung_thread_limit`` seconds so far.  So if you get
        *lots* of requests but they complete in a reasonable amount of time,
        the requests will simply queue up (adding more threads probably
        wouldn't speed them up).  But if you have lots of hung threads and
        one more request comes in, this will add workers to handle it.
        Default 5.

    ``threadpool_max_zombie_threads_before_die``:

        If there are more zombies than this, just kill the process.  This is
        only good if you have a monitor that will automatically restart
        the server.  This can clean up the mess.  Default 0 (disabled).

    `threadpool_hung_check_period``:

        Every X requests, check for hung threads that need to be killed,
        or for zombie threads that should cause a restart.  Default 100
        requests.

    ``threadpool_logger``:

        Logging messages will go the logger named here.

    ``threadpool_error_email`` (or global ``error_email`` setting):

        When threads are killed or the process restarted, this email
        address will be contacted (using an SMTP server on localhost).

"""


if __name__ == '__main__':
    from paste.wsgilib import dump_environ
    #serve(dump_environ, ssl_pem="test.pem")
    serve(dump_environ, server_version="Wombles/1.0",
          protocol_version="HTTP/1.1", port="8888")
