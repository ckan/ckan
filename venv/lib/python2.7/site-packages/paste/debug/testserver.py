# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# This code was written with funding by http://prometheusresearch.com
"""
WSGI Test Server

This builds upon paste.util.baseserver to customize it for regressions
where using raw_interactive won't do.


"""
import time
from paste.httpserver import *

class WSGIRegressionServer(WSGIServer):
    """
    A threaded WSGIServer for use in regression testing.  To use this
    module, call serve(application, regression=True), and then call
    server.accept() to let it handle one request.  When finished, use
    server.stop() to shutdown the server. Note that all pending requests
    are processed before the server shuts down.
    """
    defaulttimeout = 10
    def __init__ (self, *args, **kwargs):
        WSGIServer.__init__(self, *args, **kwargs)
        self.stopping = []
        self.pending = []
        self.timeout = self.defaulttimeout
        # this is a local connection, be quick
        self.socket.settimeout(2) 
    def serve_forever(self):
        from threading import Thread
        thread = Thread(target=self.serve_pending)
        thread.start()
    def reset_expires(self):
        if self.timeout:
            self.expires = time.time() + self.timeout
    def close_request(self, *args, **kwargs):
        WSGIServer.close_request(self, *args, **kwargs)
        self.pending.pop()
        self.reset_expires()
    def serve_pending(self):
        self.reset_expires()
        while not self.stopping or self.pending:
            now = time.time()
            if now > self.expires and self.timeout:
                # note regression test doesn't handle exceptions in
                # threads very well; so we just print and exit
                print "\nWARNING: WSGIRegressionServer timeout exceeded\n"
                break
            if self.pending:
                self.handle_request()
            time.sleep(.1)
    def stop(self):
        """ stop the server (called from tester's thread) """
        self.stopping.append(True)
    def accept(self, count = 1):
        """ accept another request (called from tester's thread) """
        assert not self.stopping
        [self.pending.append(True) for x in range(count)]

def serve(application, host=None, port=None, handler=None):
    server = WSGIRegressionServer(application, host, port, handler)
    print "serving on %s:%s" % server.server_address
    server.serve_forever()
    return server

if __name__ == '__main__':
    import urllib
    from paste.wsgilib import dump_environ
    server = serve(dump_environ)
    baseuri = ("http://%s:%s" % server.server_address)

    def fetch(path):
        # tell the server to humor exactly one more request
        server.accept(1)
        # not needed; but this is what you do if the server 
        # may not respond in a resonable time period
        import socket
        socket.setdefaulttimeout(5)
        # build a uri, fetch and return
        return urllib.urlopen(baseuri + path).read()
      
    assert "PATH_INFO: /foo" in fetch("/foo")
    assert "PATH_INFO: /womble" in fetch("/womble")

    # ok, let's make one more final request...
    server.accept(1)
    # and then schedule a stop()
    server.stop()
    # and then... fetch it...
    urllib.urlopen(baseuri)
