# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# This code was written with funding by http://prometheusresearch.com
"""
Various Applications for Debugging/Testing Purposes
"""

import time
__all__ = ['SimpleApplication', 'SlowConsumer']


class SimpleApplication(object):
    """
    Produces a simple web page
    """
    def __call__(self, environ, start_response):
        body = "<html><body>simple</body></html>"
        start_response("200 OK", [('Content-Type', 'text/html'),
                                  ('Content-Length', str(len(body)))])
        return [body]

class SlowConsumer(object):
    """
    Consumes an upload slowly...

    NOTE: This should use the iterator form of ``wsgi.input``,
          but it isn't implemented in paste.httpserver.
    """
    def __init__(self, chunk_size = 4096, delay = 1, progress = True):
        self.chunk_size = chunk_size
        self.delay = delay
        self.progress = True

    def __call__(self, environ, start_response):
        size = 0
        total  = environ.get('CONTENT_LENGTH')
        if total:
            remaining = int(total)
            while remaining > 0:
                if self.progress:
                    print "%s of %s remaining" % (remaining, total)
                if remaining > 4096:
                    chunk = environ['wsgi.input'].read(4096)
                else:
                    chunk = environ['wsgi.input'].read(remaining)
                if not chunk:
                    break
                size += len(chunk)
                remaining -= len(chunk)
                if self.delay:
                    time.sleep(self.delay)
            body = "<html><body>%d bytes</body></html>" % size
        else:
            body = ('<html><body>\n'
                '<form method="post" enctype="multipart/form-data">\n'
                '<input type="file" name="file">\n'
                '<input type="submit" >\n'
                '</form></body></html>\n')
        print "bingles"
        start_response("200 OK", [('Content-Type', 'text/html'),
                                  ('Content-Length', len(body))])
        return [body]

def make_test_app(global_conf):
    return SimpleApplication()

make_test_app.__doc__ = SimpleApplication.__doc__

def make_slow_app(global_conf, chunk_size=4096, delay=1, progress=True):
    from paste.deploy.converters import asbool
    return SlowConsumer(
        chunk_size=int(chunk_size),
        delay=int(delay),
        progress=asbool(progress))

make_slow_app.__doc__ = SlowConsumer.__doc__
