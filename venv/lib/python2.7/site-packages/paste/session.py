# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

"""
Creates a session object in your WSGI environment.

Use like:

..code-block:: Python

    environ['paste.session.factory']()

This will return a dictionary.  The contents of this dictionary will
be saved to disk when the request is completed.  The session will be
created when you first fetch the session dictionary, and a cookie will
be sent in that case.  There's current no way to use sessions without
cookies, and there's no way to delete a session except to clear its
data.

@@: This doesn't do any locking, and may cause problems when a single
session is accessed concurrently.  Also, it loads and saves the
session for each request, with no caching.  Also, sessions aren't
expired.
"""

from Cookie import SimpleCookie
import time
import random
import os
import datetime
import threading
import tempfile

try:
    import cPickle
except ImportError:
    import pickle as cPickle
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
from paste import wsgilib
from paste import request

class SessionMiddleware(object):

    def __init__(self, application, global_conf=None, **factory_kw):
        self.application = application
        self.factory_kw = factory_kw

    def __call__(self, environ, start_response):
        session_factory = SessionFactory(environ, **self.factory_kw)
        environ['paste.session.factory'] = session_factory
        remember_headers = []

        def session_start_response(status, headers, exc_info=None):
            if not session_factory.created:
                remember_headers[:] = [status, headers]
                return start_response(status, headers)
            headers.append(session_factory.set_cookie_header())
            return start_response(status, headers, exc_info)

        app_iter = self.application(environ, session_start_response)
        def start():
            if session_factory.created and remember_headers:
                # Tricky bastard used the session after start_response
                status, headers = remember_headers
                headers.append(session_factory.set_cookie_header())
                exc = ValueError(
                    "You cannot get the session after content from the "
                    "app_iter has been returned")
                start_response(status, headers, (exc.__class__, exc, None))
        def close():
            if session_factory.used:
                session_factory.close()
        return wsgilib.add_start_close(app_iter, start, close)


class SessionFactory(object):


    def __init__(self, environ, cookie_name='_SID_',
                 session_class=None,
                 session_expiration=60*12, # in minutes
                 **session_class_kw):

        self.created = False
        self.used = False
        self.environ = environ
        self.cookie_name = cookie_name
        self.session = None
        self.session_class = session_class or FileSession
        self.session_class_kw = session_class_kw

        self.expiration = session_expiration

    def __call__(self):
        self.used = True
        if self.session is not None:
            return self.session.data()
        cookies = request.get_cookies(self.environ)
        session = None
        if cookies.has_key(self.cookie_name):
            self.sid = cookies[self.cookie_name].value
            try:
                session = self.session_class(self.sid, create=False,
                                             **self.session_class_kw)
            except KeyError:
                # Invalid SID
                pass
        if session is None:
            self.created = True
            self.sid = self.make_sid()
            session = self.session_class(self.sid, create=True,
                                         **self.session_class_kw)
        session.clean_up()
        self.session = session
        return session.data()

    def has_session(self):
        if self.session is not None:
            return True
        cookies = request.get_cookies(self.environ)
        if cookies.has_key(self.cookie_name):
            return True
        return False

    def make_sid(self):
        # @@: need better algorithm
        return (''.join(['%02d' % x for x in time.localtime(time.time())[:6]])
                + '-' + self.unique_id())

    def unique_id(self, for_object=None):
        """
        Generates an opaque, identifier string that is practically
        guaranteed to be unique.  If an object is passed, then its
        id() is incorporated into the generation.  Relies on md5 and
        returns a 32 character long string.
        """
        r = [time.time(), random.random()]
        if hasattr(os, 'times'):
            r.append(os.times())
        if for_object is not None:
            r.append(id(for_object))
        md5_hash = md5(str(r))
        try:
            return md5_hash.hexdigest()
        except AttributeError:
            # Older versions of Python didn't have hexdigest, so we'll
            # do it manually
            hexdigest = []
            for char in md5_hash.digest():
                hexdigest.append('%02x' % ord(char))
            return ''.join(hexdigest)

    def set_cookie_header(self):
        c = SimpleCookie()
        c[self.cookie_name] = self.sid
        c[self.cookie_name]['path'] = '/'

        gmt_expiration_time = time.gmtime(time.time() + (self.expiration * 60))
        c[self.cookie_name]['expires'] = time.strftime("%a, %d-%b-%Y %H:%M:%S GMT", gmt_expiration_time)

        name, value = str(c).split(': ', 1)
        return (name, value)

    def close(self):
        if self.session is not None:
            self.session.close()


last_cleanup = None
cleaning_up = False
cleanup_cycle = datetime.timedelta(seconds=15*60) #15 min

class FileSession(object):

    def __init__(self, sid, create=False, session_file_path=tempfile.gettempdir(),
                 chmod=None,
                 expiration=2880, # in minutes: 48 hours
                 ):
        if chmod and isinstance(chmod, basestring):
            chmod = int(chmod, 8)
        self.chmod = chmod
        if not sid:
            # Invalid...
            raise KeyError
        self.session_file_path = session_file_path
        self.sid = sid
        if not create:
            if not os.path.exists(self.filename()):
                raise KeyError
        self._data = None

        self.expiration = expiration


    def filename(self):
        return os.path.join(self.session_file_path, self.sid)

    def data(self):
        if self._data is not None:
            return self._data
        if os.path.exists(self.filename()):
            f = open(self.filename(), 'rb')
            self._data = cPickle.load(f)
            f.close()
        else:
            self._data = {}
        return self._data

    def close(self):
        if self._data is not None:
            filename = self.filename()
            exists = os.path.exists(filename)
            if not self._data:
                if exists:
                    os.unlink(filename)
            else:
                f = open(filename, 'wb')
                cPickle.dump(self._data, f)
                f.close()
                if not exists and self.chmod:
                    os.chmod(filename, self.chmod)

    def _clean_up(self):
        global cleaning_up
        try:
            exp_time = datetime.timedelta(seconds=self.expiration*60)
            now = datetime.datetime.now()

            #Open every session and check that it isn't too old
            for root, dirs, files in os.walk(self.session_file_path):
                for f in files:
                    self._clean_up_file(f, exp_time=exp_time, now=now)
        finally:
            cleaning_up = False

    def _clean_up_file(self, f, exp_time, now):
        t = f.split("-")
        if len(t) != 2:
            return
        t = t[0]
        try:
            sess_time = datetime.datetime(
                    int(t[0:4]),
                    int(t[4:6]),
                    int(t[6:8]),
                    int(t[8:10]),
                    int(t[10:12]),
                    int(t[12:14]))
        except ValueError:
            # Probably not a session file at all
            return

        if sess_time + exp_time < now:
            os.remove(os.path.join(self.session_file_path, f))

    def clean_up(self):
        global last_cleanup, cleanup_cycle, cleaning_up
        now = datetime.datetime.now()

        if cleaning_up:
            return

        if not last_cleanup or last_cleanup + cleanup_cycle < now:
            if not cleaning_up:
                cleaning_up = True
                try:
                    last_cleanup = now
                    t = threading.Thread(target=self._clean_up)
                    t.start()
                except:
                    # Normally _clean_up should set cleaning_up
                    # to false, but if something goes wrong starting
                    # it...
                    cleaning_up = False
                    raise

class _NoDefault(object):
    def __repr__(self):
        return '<dynamic default>'
NoDefault = _NoDefault()

def make_session_middleware(
    app, global_conf,
    session_expiration=NoDefault,
    expiration=NoDefault,
    cookie_name=NoDefault,
    session_file_path=NoDefault,
    chmod=NoDefault):
    """
    Adds a middleware that handles sessions for your applications.
    The session is a peristent dictionary.  To get this dictionary
    in your application, use ``environ['paste.session.factory']()``
    which returns this persistent dictionary.

    Configuration:

      session_expiration:
          The time each session lives, in minutes.  This controls
          the cookie expiration.  Default 12 hours.

      expiration:
          The time each session lives on disk.  Old sessions are
          culled from disk based on this.  Default 48 hours.

      cookie_name:
          The cookie name used to track the session.  Use different
          names to avoid session clashes.

      session_file_path:
          Sessions are put in this location, default /tmp.

      chmod:
          The octal chmod you want to apply to new sessions (e.g., 660
          to make the sessions group readable/writable)

    Each of these also takes from the global configuration.  cookie_name
    and chmod take from session_cookie_name and session_chmod
    """
    if session_expiration is NoDefault:
        session_expiration = global_conf.get('session_expiration', 60*12)
    session_expiration = int(session_expiration)
    if expiration is NoDefault:
        expiration = global_conf.get('expiration', 60*48)
    expiration = int(expiration)
    if cookie_name is NoDefault:
        cookie_name = global_conf.get('session_cookie_name', '_SID_')
    if session_file_path is NoDefault:
        session_file_path = global_conf.get('session_file_path', '/tmp')
    if chmod is NoDefault:
        chmod = global_conf.get('session_chmod', None)
    return SessionMiddleware(
        app, session_expiration=session_expiration,
        expiration=expiration, cookie_name=cookie_name,
        session_file_path=session_file_path, chmod=chmod)
