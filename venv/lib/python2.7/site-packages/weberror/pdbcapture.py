from webob import Request, Response
import threading
from paste.util import threadedprint
from itertools import count
import tempita
from paste.urlparser import StaticURLParser
from paste.util.filemixin import FileMixin
import os
import sys

try:
    import json
except ImportError: # pragma: no cover
    import simplejson as json

here = os.path.dirname(os.path.abspath(__file__))

#def debug(msg, *args):
#    args = '%s %s' % (msg, ' '.join(map(repr, args)))
#    print >> sys.stderr, args

class PdbCapture(object):

    def __init__(self, app):
        self.app = app
        threadedprint.install(leave_stdout=True)
        threadedprint.install_stdin()
        self.counter = count()
        self.static_app = StaticURLParser(os.path.join(here, 'pdbcapture/static'))
        self.media_app = StaticURLParser(os.path.join(here, 'eval-media'))
        self.states = {}

    def get_template(self, template_name):
        filename = os.path.join(os.path.dirname(__file__), template_name)
        return tempita.HTMLTemplate.from_filename(filename)
        
    def __call__(self, environ, start_response):
        req = Request(environ)
        if req.GET.get('__pdbid__'):
            id = int(req.GET['__pdbid__'])
            response = self.states[id]['response']
            return response(environ, start_response)
        if req.path_info_peek() == '.pdbcapture':
            req.path_info_pop()
            if req.path_info_peek() == 'static':
                req.path_info_pop()
                return self.static_app(environ, start_response)
            if req.path_info_peek() == 'media':
                req.path_info_pop()
                return self.media_app(environ, start_response)
            resp = self.internal_request(req)
            return resp(environ, start_response)
        id = self.counter.next()
        state = dict(id=id,
                     event=threading.Event(),
                     base_url=req.application_url,
                     stdout=[],
                     stdin=[],
                     stdin_event=threading.Event())
        t = threading.Thread(target=self.call_app, args=(req, state))
        t.setDaemon(True)
        t.start()
        state['event'].wait()
        if 'response' in state:
            # Normal request, nothing happened
            resp = state['response']
            return resp(environ, start_response)
        if 'exc_info' in state:
            raise state['exc_info'][0], state['exc_info'][1], state['exc_info'][2]
        self.states[id] = state
        tmpl = self.get_template('pdbcapture_response.html')
        body = tmpl.substitute(req=req, state=state, id=id)
        resp = Response(body)
        return resp(environ, start_response)

    def internal_request(self, req):
        id = int(req.params['id'])
        state = self.states[id]
        if 'response' in state:
            body = {'response': 1}
        else:
            if req.params.get('stdin'):
                state['stdin'].append(req.params['stdin'])
                state['stdin_event'].set()
            stdout = ''.join(state['stdout'])
            state['stdout'][:] = []
            body = {'stdout': stdout}
        if not state['stdin_event'].isSet():
            body['stdinPending'] = 1
        resp = Response(content_type='application/json',
                        body=json.dumps(body))
        return resp

    def call_app(self, req, state):
        event = state['event']
        stream_handler = StreamHandler(stdin=state['stdin'], stdin_event=state['stdin_event'], stdout=state['stdout'],
                                       signal_event=state['event'])
        threadedprint.register(stream_handler)
        threadedprint.register_stdin(stream_handler)
        try:
            resp = req.get_response(self.app)
            state['response'] = resp
        except:
            state['exc_info'] = sys.exc_info()
        event.set()

class StreamHandler(FileMixin):

    def __init__(self, stdin, stdout, stdin_event, signal_event):
        self.stdin = stdin
        self.stdout = stdout
        self.stdin_event = stdin_event
        self.signal_event = signal_event

    def write(self, text):
        self.stdout.append(text)

    def read(self, size=None):
        self.signal_event.set()
        text = ''.join(self.stdin)
        if size is None or size == -1:
            self.stdin[:] = []
            sys.stdout.write(text)
            return text
        while len(text) < size:
            self.stdin_event.clear()
            self.stdin_event.wait()
            text = ''.join(self.stdin)
        pending = text[:size]
        self.stdin[:] = [text[size:]]
        sys.stdout.write(pending)
        return pending

def test_app(environ, start_response):
    import pdb
    message = "Hey, what's up?"
    pdb.set_trace()
    start_response('200 OK', [('Content-type', 'text/plain')])
    return [message]

if __name__ == '__main__':
    from paste import httpserver
    httpserver.serve(PdbCapture(test_app))
    
