import os

import SimpleHTTPServer
import SocketServer
from threading import Thread

PORT = 50001


def serve(port=PORT):
    '''Serves static test files over HTTP'''

    # Make sure we serve from the tests' static directory
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'static'))

    Handler = SimpleHTTPServer.SimpleHTTPRequestHandler

    class TestServer(SocketServer.TCPServer):
        allow_reuse_address = True

    httpd = TestServer(("", PORT), Handler)

    print 'Serving test HTTP server at port', PORT

    httpd_thread = Thread(target=httpd.serve_forever)
    httpd_thread.setDaemon(True)
    httpd_thread.start()
