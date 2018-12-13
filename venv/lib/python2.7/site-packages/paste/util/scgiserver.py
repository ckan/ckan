"""
SCGI-->WSGI application proxy, "SWAP".

(Originally written by Titus Brown.)

This lets an SCGI front-end like mod_scgi be used to execute WSGI
application objects.  To use it, subclass the SWAP class like so::

   class TestAppHandler(swap.SWAP):
       def __init__(self, *args, **kwargs):
           self.prefix = '/canal'
           self.app_obj = TestAppClass
           swap.SWAP.__init__(self, *args, **kwargs)

where 'TestAppClass' is the application object from WSGI and '/canal'
is the prefix for what is served by the SCGI Web-server-side process.

Then execute the SCGI handler "as usual" by doing something like this::

   scgi_server.SCGIServer(TestAppHandler, port=4000).serve()

and point mod_scgi (or whatever your SCGI front end is) at port 4000.

Kudos to the WSGI folk for writing a nice PEP & the Quixote folk for
writing a nice extensible SCGI server for Python!
"""

import sys
import time
from scgi import scgi_server

def debug(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S",
                              time.localtime(time.time()))
    sys.stderr.write("[%s] %s\n" % (timestamp, msg))

class SWAP(scgi_server.SCGIHandler):
    """
    SCGI->WSGI application proxy: let an SCGI server execute WSGI
    application objects.
    """
    app_obj = None
    prefix = None
    
    def __init__(self, *args, **kwargs):
        assert self.app_obj, "must set app_obj"
        assert self.prefix is not None, "must set prefix"
        args = (self,) + args
        scgi_server.SCGIHandler.__init__(*args, **kwargs)

    def handle_connection(self, conn):
        """
        Handle an individual connection.
        """
        input = conn.makefile("r")
        output = conn.makefile("w")

        environ = self.read_env(input)
        environ['wsgi.input']        = input
        environ['wsgi.errors']       = sys.stderr
        environ['wsgi.version']      = (1, 0)
        environ['wsgi.multithread']  = False
        environ['wsgi.multiprocess'] = True
        environ['wsgi.run_once']     = False

        # dunno how SCGI does HTTPS signalling; can't test it myself... @CTB
        if environ.get('HTTPS','off') in ('on','1'):
            environ['wsgi.url_scheme'] = 'https'
        else:
            environ['wsgi.url_scheme'] = 'http'

        ## SCGI does some weird environ manglement.  We need to set
        ## SCRIPT_NAME from 'prefix' and then set PATH_INFO from
        ## REQUEST_URI.

        prefix = self.prefix
        path = environ['REQUEST_URI'][len(prefix):].split('?', 1)[0]

        environ['SCRIPT_NAME'] = prefix
        environ['PATH_INFO'] = path

        headers_set = []
        headers_sent = []
        chunks = []
        def write(data):
            chunks.append(data)
        
        def start_response(status, response_headers, exc_info=None):
            if exc_info:
                try:
                    if headers_sent:
                        # Re-raise original exception if headers sent
                        raise exc_info[0], exc_info[1], exc_info[2]
                finally:
                    exc_info = None     # avoid dangling circular ref
            elif headers_set:
                raise AssertionError("Headers already set!")

            headers_set[:] = [status, response_headers]
            return write

        ###

        result = self.app_obj(environ, start_response)
        try:
            for data in result:
                chunks.append(data)
                
            # Before the first output, send the stored headers
            if not headers_set:
                # Error -- the app never called start_response
                status = '500 Server Error'
                response_headers = [('Content-type', 'text/html')]
                chunks = ["XXX start_response never called"]
            else:
                status, response_headers = headers_sent[:] = headers_set
                
            output.write('Status: %s\r\n' % status)
            for header in response_headers:
                output.write('%s: %s\r\n' % header)
            output.write('\r\n')

            for data in chunks:
                output.write(data)
        finally:
            if hasattr(result,'close'):
                result.close()

        # SCGI backends use connection closing to signal 'fini'.
        try:
            input.close()
            output.close()
            conn.close()
        except IOError, err:
            debug("IOError while closing connection ignored: %s" % err)


def serve_application(application, prefix, port=None, host=None, max_children=None):
    """
    Serve the specified WSGI application via SCGI proxy.

    ``application``
        The WSGI application to serve.

    ``prefix``
        The prefix for what is served by the SCGI Web-server-side process.

    ``port``
        Optional port to bind the SCGI proxy to. Defaults to SCGIServer's
        default port value.

    ``host``
        Optional host to bind the SCGI proxy to. Defaults to SCGIServer's
        default host value.

    ``host``
        Optional maximum number of child processes the SCGIServer will
        spawn. Defaults to SCGIServer's default max_children value.
    """
    class SCGIAppHandler(SWAP):
        def __init__ (self, *args, **kwargs):
            self.prefix = prefix
            self.app_obj = application
            SWAP.__init__(self, *args, **kwargs)

    kwargs = dict(handler_class=SCGIAppHandler)
    for kwarg in ('host', 'port', 'max_children'):
        if locals()[kwarg] is not None:
            kwargs[kwarg] = locals()[kwarg]

    scgi_server.SCGIServer(**kwargs).serve()
