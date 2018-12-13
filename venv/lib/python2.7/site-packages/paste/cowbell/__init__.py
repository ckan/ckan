# Cowbell images: http://commons.wikimedia.org/wiki/Image:Cowbell-1.jpg
import os
import re
from paste.fileapp import FileApp
from paste.response import header_value, remove_header

SOUND = "http://www.c-eye.net/eyeon/WalkenWAVS/explorestudiospace.wav"

class MoreCowbell(object):
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        script_name = environ.get('SCRIPT_NAME', '')
        for filename in ['bell-ascending.png', 'bell-descending.png']:
            if path_info == '/.cowbell/'+ filename:
                app = FileApp(os.path.join(os.path.dirname(__file__), filename))
                return app(environ, start_response)
        type = []
        body = []
        def repl_start_response(status, headers, exc_info=None):
            ct = header_value(headers, 'content-type')
            if ct and ct.startswith('text/html'):
                type.append(ct)
                remove_header(headers, 'content-length')
                start_response(status, headers, exc_info)
                return body.append
            return start_response(status, headers, exc_info)
        app_iter = self.app(environ, repl_start_response)
        if type:
            # Got text/html
            body.extend(app_iter)
            body = ''.join(body)
            body = insert_head(body, self.javascript.replace('__SCRIPT_NAME__', script_name))
            body = insert_body(body, self.resources.replace('__SCRIPT_NAME__', script_name))
            return [body]
        else:
            return app_iter

    javascript = '''\
<script type="text/javascript">
var cowbellState = 'hidden';
var lastCowbellPosition = null;
function showSomewhere() {
  var sec, el;
  if (cowbellState == 'hidden') {
    el = document.getElementById('cowbell-ascending');
    lastCowbellPosition = [parseInt(Math.random()*(window.innerWidth-200)), 
                           parseInt(Math.random()*(window.innerHeight-200))];
    el.style.left = lastCowbellPosition[0] + 'px';
    el.style.top = lastCowbellPosition[1] + 'px';
    el.style.display = '';
    cowbellState = 'ascending';
    sec = 1;
  } else if (cowbellState == 'ascending') {
    document.getElementById('cowbell-ascending').style.display = 'none';
    el = document.getElementById('cowbell-descending');
    el.style.left = lastCowbellPosition[0] + 'px';
    el.style.top = lastCowbellPosition[1] + 'px';
    el.style.display = '';
    cowbellState = 'descending';
    sec = 1;
  } else {
    document.getElementById('cowbell-descending').style.display = 'none';
    cowbellState = 'hidden';
    sec = Math.random()*20;
  }
  setTimeout(showSomewhere, sec*1000);
}
setTimeout(showSomewhere, Math.random()*20*1000);
</script>
'''

    resources = '''\
<div id="cowbell-ascending" style="display: none; position: fixed">
<img src="__SCRIPT_NAME__/.cowbell/bell-ascending.png">
</div>
<div id="cowbell-descending" style="display: none; position: fixed">
<img src="__SCRIPT_NAME__/.cowbell/bell-descending.png">
</div>
'''

def insert_head(body, text):
    end_head = re.search(r'</head>', body, re.I)
    if end_head:
        return body[:end_head.start()] + text + body[end_head.end():]
    else:
        return text + body

def insert_body(body, text):
    end_body = re.search(r'</body>', body, re.I)
    if end_body:
        return body[:end_body.start()] + text + body[end_body.end():]
    else:
        return body + text

def make_cowbell(global_conf, app):
    return MoreCowbell(app)

if __name__ == '__main__':
    from paste.debug.debugapp import SimpleApplication
    app = MoreCowbell(SimpleApplication())
    from paste.httpserver import serve
    serve(app)
