import os

import SimpleHTTPServer
import SocketServer
from threading import Thread

PORT = 50001


class StaticHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def send_head(self):
        if 'huge.json' in self.path:
            f = open(self.translate_path(self.path), 'rb')
            self.send_response(200)
            self.send_header("Content-type", 'application/json')
            self.send_header("Content-Length", '1000000000')
            self.end_headers()
            return f
        else:
            return SimpleHTTPServer.SimpleHTTPRequestHandler.send_head(self)

    def log_message(self, *args):
        pass

def serve(port=PORT):
    '''Serves static test files over HTTP'''

    # Make sure we serve from the tests' static directory
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'static'))

    Handler = StaticHandler

    class TestServer(SocketServer.TCPServer):
        allow_reuse_address = True

    httpd = TestServer(("", PORT), Handler)

    print 'Serving test HTTP server at port', PORT

    httpd_thread = Thread(target=httpd.serve_forever)
    httpd_thread.setDaemon(True)
    httpd_thread.start()
