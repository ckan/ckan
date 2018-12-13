"""
Watches the key ``paste.httpserver.thread_pool`` to see how many
threads there are and report on any wedged threads.
"""
import sys
import cgi
import time
import traceback
from cStringIO import StringIO
from thread import get_ident
from paste import httpexceptions
from paste.request import construct_url, parse_formvars
from paste.util.template import HTMLTemplate, bunch

page_template = HTMLTemplate('''
<html>
 <head>
  <style type="text/css">
   body {
     font-family: sans-serif;
   }
   table.environ tr td {
     border-bottom: #bbb 1px solid;
   }
   table.environ tr td.bottom {
     border-bottom: none;
   }
   table.thread {
     border: 1px solid #000;
     margin-bottom: 1em;
   }
   table.thread tr td {
     border-bottom: #999 1px solid;
     padding-right: 1em;
   }
   table.thread tr td.bottom {
     border-bottom: none;
   }
   table.thread tr.this_thread td {
     background-color: #006;
     color: #fff;
   }
   a.button {
     background-color: #ddd;
     border: #aaa outset 2px;
     text-decoration: none;
     margin-top: 10px;
     font-size: 80%;
     color: #000;
   }
   a.button:hover {
     background-color: #eee;
     border: #bbb outset 2px;
   }
   a.button:active {
     border: #bbb inset 2px;
   }
  </style>
  <title>{{title}}</title>
 </head>
 <body>
  <h1>{{title}}</h1>
  {{if kill_thread_id}}
  <div style="background-color: #060; color: #fff;
              border: 2px solid #000;">
  Thread {{kill_thread_id}} killed
  </div>
  {{endif}}
  <div>Pool size: {{nworkers}}
       {{if actual_workers > nworkers}}
         + {{actual_workers-nworkers}} extra
       {{endif}}
       ({{nworkers_used}} used including current request)<br>
       idle: {{len(track_threads["idle"])}},
       busy: {{len(track_threads["busy"])}},
       hung: {{len(track_threads["hung"])}},
       dying: {{len(track_threads["dying"])}},
       zombie: {{len(track_threads["zombie"])}}</div>

{{for thread in threads}}

<table class="thread">
 <tr {{if thread.thread_id == this_thread_id}}class="this_thread"{{endif}}>
  <td>
   <b>Thread</b>
   {{if thread.thread_id == this_thread_id}}
   (<i>this</i> request)
   {{endif}}</td>
  <td>
   <b>{{thread.thread_id}}
    {{if allow_kill}}
    <form action="{{script_name}}/kill" method="POST"
          style="display: inline">
      <input type="hidden" name="thread_id" value="{{thread.thread_id}}">
      <input type="submit" value="kill">
    </form>
    {{endif}}
   </b>
  </td>
 </tr>
 <tr>
  <td>Time processing request</td>
  <td>{{thread.time_html|html}}</td>
 </tr>
 <tr>
  <td>URI</td>
  <td>{{if thread.uri == 'unknown'}}
      unknown
      {{else}}<a href="{{thread.uri}}">{{thread.uri_short}}</a>
      {{endif}}
  </td>
 <tr>
  <td colspan="2" class="bottom">
   <a href="#" class="button" style="width: 9em; display: block"
      onclick="
        var el = document.getElementById('environ-{{thread.thread_id}}');
        if (el.style.display) {
            el.style.display = '';
            this.innerHTML = \'&#9662; Hide environ\';
        } else {
            el.style.display = 'none';
            this.innerHTML = \'&#9656; Show environ\';
        }
        return false
      ">&#9656; Show environ</a>
   
   <div id="environ-{{thread.thread_id}}" style="display: none">
    {{if thread.environ:}}
    <table class="environ">
     {{for loop, item in looper(sorted(thread.environ.items()))}}
     {{py:key, value=item}}
     <tr>
      <td {{if loop.last}}class="bottom"{{endif}}>{{key}}</td>
      <td {{if loop.last}}class="bottom"{{endif}}>{{value}}</td>
     </tr>
     {{endfor}}
    </table>
    {{else}}
    Thread is in process of starting
    {{endif}}
   </div>

   {{if thread.traceback}}
   <a href="#" class="button" style="width: 9em; display: block"
      onclick="
        var el = document.getElementById('traceback-{{thread.thread_id}}');
        if (el.style.display) {
            el.style.display = '';
            this.innerHTML = \'&#9662; Hide traceback\';
        } else {
            el.style.display = 'none';
            this.innerHTML = \'&#9656; Show traceback\';
        }
        return false
      ">&#9656; Show traceback</a>

    <div id="traceback-{{thread.thread_id}}" style="display: none">
      <pre class="traceback">{{thread.traceback}}</pre>
    </div>
    {{endif}}

  </td>
 </tr>
</table>

{{endfor}}

 </body>
</html>
''', name='watchthreads.page_template')

class WatchThreads(object):

    """
    Application that watches the threads in ``paste.httpserver``,
    showing the length each thread has been working on a request.

    If allow_kill is true, then you can kill errant threads through
    this application.

    This application can expose private information (specifically in
    the environment, like cookies), so it should be protected.
    """

    def __init__(self, allow_kill=False):
        self.allow_kill = allow_kill

    def __call__(self, environ, start_response):
        if 'paste.httpserver.thread_pool' not in environ:
            start_response('403 Forbidden', [('Content-type', 'text/plain')])
            return ['You must use the threaded Paste HTTP server to use this application']
        if environ.get('PATH_INFO') == '/kill':
            return self.kill(environ, start_response)
        else:
            return self.show(environ, start_response)

    def show(self, environ, start_response):
        start_response('200 OK', [('Content-type', 'text/html')])
        form = parse_formvars(environ)
        if form.get('kill'):
            kill_thread_id = form['kill']
        else:
            kill_thread_id = None
        thread_pool = environ['paste.httpserver.thread_pool']
        nworkers = thread_pool.nworkers
        now = time.time()


        workers = thread_pool.worker_tracker.items()
        workers.sort(key=lambda v: v[1][0])
        threads = []
        for thread_id, (time_started, worker_environ) in workers:
            thread = bunch()
            threads.append(thread)
            if worker_environ:
                thread.uri = construct_url(worker_environ)
            else:
                thread.uri = 'unknown'
            thread.thread_id = thread_id
            thread.time_html = format_time(now-time_started)
            thread.uri_short = shorten(thread.uri)
            thread.environ = worker_environ
            thread.traceback = traceback_thread(thread_id)
            
        page = page_template.substitute(
            title="Thread Pool Worker Tracker",
            nworkers=nworkers,
            actual_workers=len(thread_pool.workers),
            nworkers_used=len(workers),
            script_name=environ['SCRIPT_NAME'],
            kill_thread_id=kill_thread_id,
            allow_kill=self.allow_kill,
            threads=threads,
            this_thread_id=get_ident(),
            track_threads=thread_pool.track_threads())

        return [page]

    def kill(self, environ, start_response):
        if not self.allow_kill:
            exc = httpexceptions.HTTPForbidden(
                'Killing threads has not been enabled.  Shame on you '
                'for trying!')
            return exc(environ, start_response)
        vars = parse_formvars(environ)
        thread_id = int(vars['thread_id'])
        thread_pool = environ['paste.httpserver.thread_pool']
        if thread_id not in thread_pool.worker_tracker:
            exc = httpexceptions.PreconditionFailed(
                'You tried to kill thread %s, but it is not working on '
                'any requests' % thread_id)
            return exc(environ, start_response)
        thread_pool.kill_worker(thread_id)
        script_name = environ['SCRIPT_NAME'] or '/'
        exc = httpexceptions.HTTPFound(
            headers=[('Location', script_name+'?kill=%s' % thread_id)])
        return exc(environ, start_response)
        
def traceback_thread(thread_id):
    """
    Returns a plain-text traceback of the given thread, or None if it
    can't get a traceback.
    """
    if not hasattr(sys, '_current_frames'):
        # Only 2.5 has support for this, with this special function
        return None
    frames = sys._current_frames()
    if not thread_id in frames:
        return None
    frame = frames[thread_id]
    out = StringIO()
    traceback.print_stack(frame, file=out)
    return out.getvalue()

hide_keys = ['paste.httpserver.thread_pool']

def format_environ(environ):
    if environ is None:
        return environ_template.substitute(
            key='---',
            value='No environment registered for this thread yet')
    environ_rows = []
    for key, value in sorted(environ.items()):
        if key in hide_keys:
            continue
        try:
            if key.upper() != key:
                value = repr(value)
            environ_rows.append(
                environ_template.substitute(
                key=cgi.escape(str(key)),
                value=cgi.escape(str(value))))
        except Exception, e:
            environ_rows.append(
                environ_template.substitute(
                key=cgi.escape(str(key)),
                value='Error in <code>repr()</code>: %s' % e))
    return ''.join(environ_rows)
    
def format_time(time_length):
    if time_length >= 60*60:
        # More than an hour
        time_string = '%i:%02i:%02i' % (int(time_length/60/60),
                                        int(time_length/60) % 60,
                                        time_length % 60)
    elif time_length >= 120:
        time_string = '%i:%02i' % (int(time_length/60),
                                   time_length % 60)
    elif time_length > 60:
        time_string = '%i sec' % time_length
    elif time_length > 1:
        time_string = '%0.1f sec' % time_length
    else:
        time_string = '%0.2f sec' % time_length
    if time_length < 5:
        return time_string
    elif time_length < 120:
        return '<span style="color: #900">%s</span>' % time_string
    else:
        return '<span style="background-color: #600; color: #fff">%s</span>' % time_string

def shorten(s):
    if len(s) > 60:
        return s[:40]+'...'+s[-10:]
    else:
        return s

def make_watch_threads(global_conf, allow_kill=False):
    from paste.deploy.converters import asbool
    return WatchThreads(allow_kill=asbool(allow_kill))
make_watch_threads.__doc__ = WatchThreads.__doc__

def make_bad_app(global_conf, pause=0):
    pause = int(pause)
    def bad_app(environ, start_response):
        import thread
        if pause:
            time.sleep(pause)
        else:
            count = 0
            while 1:
                print "I'm alive %s (%s)" % (count, thread.get_ident())
                time.sleep(10)
                count += 1
        start_response('200 OK', [('content-type', 'text/plain')])
        return ['OK, paused %s seconds' % pause]
    return bad_app
