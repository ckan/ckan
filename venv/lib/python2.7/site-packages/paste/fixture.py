# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Routines for testing WSGI applications.

Most interesting is the `TestApp <class-paste.fixture.TestApp.html>`_
for testing WSGI applications, and the `TestFileEnvironment
<class-paste.fixture.TestFileEnvironment.html>`_ class for testing the
effects of command-line scripts.
"""

import sys
import random
import urllib
import urlparse
import mimetypes
import time
import cgi
import os
import shutil
import smtplib
import shlex
from Cookie import BaseCookie
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import re
try:
    import subprocess
except ImportError:
    from paste.util import subprocess24 as subprocess

from paste import wsgilib
from paste import lint
from paste.response import HeaderDict

def tempnam_no_warning(*args):
    """
    An os.tempnam with the warning turned off, because sometimes
    you just need to use this and don't care about the stupid
    security warning.
    """
    return os.tempnam(*args)

class NoDefault(object):
    pass

def sorted(l):
    l = list(l)
    l.sort()
    return l

class Dummy_smtplib(object):

    existing = None

    def __init__(self, server):
        import warnings
        warnings.warn(
            'Dummy_smtplib is not maintained and is deprecated',
            DeprecationWarning, 2)
        assert not self.existing, (
            "smtplib.SMTP() called again before Dummy_smtplib.existing.reset() "
            "called.")
        self.server = server
        self.open = True
        self.__class__.existing = self

    def quit(self):
        assert self.open, (
            "Called %s.quit() twice" % self)
        self.open = False

    def sendmail(self, from_address, to_addresses, msg):
        self.from_address = from_address
        self.to_addresses = to_addresses
        self.message = msg

    def install(cls):
        smtplib.SMTP = cls

    install = classmethod(install)

    def reset(self):
        assert not self.open, (
            "SMTP connection not quit")
        self.__class__.existing = None

class AppError(Exception):
    pass

class TestApp(object):

    # for py.test
    disabled = True

    def __init__(self, app, namespace=None, relative_to=None,
                 extra_environ=None, pre_request_hook=None,
                 post_request_hook=None):
        """
        Wraps a WSGI application in a more convenient interface for
        testing.

        ``app`` may be an application, or a Paste Deploy app
        URI, like ``'config:filename.ini#test'``.

        ``namespace`` is a dictionary that will be written to (if
        provided).  This can be used with doctest or some other
        system, and the variable ``res`` will be assigned everytime
        you make a request (instead of returning the request).

        ``relative_to`` is a directory, and filenames used for file
        uploads are calculated relative to this.  Also ``config:``
        URIs that aren't absolute.

        ``extra_environ`` is a dictionary of values that should go
        into the environment for each request.  These can provide a
        communication channel with the application.

        ``pre_request_hook`` is a function to be called prior to
        making requests (such as ``post`` or ``get``). This function
        must take one argument (the instance of the TestApp).

        ``post_request_hook`` is a function, similar to
        ``pre_request_hook``, to be called after requests are made.
        """
        if isinstance(app, (str, unicode)):
            from paste.deploy import loadapp
            # @@: Should pick up relative_to from calling module's
            # __file__
            app = loadapp(app, relative_to=relative_to)
        self.app = app
        self.namespace = namespace
        self.relative_to = relative_to
        if extra_environ is None:
            extra_environ = {}
        self.extra_environ = extra_environ
        self.pre_request_hook = pre_request_hook
        self.post_request_hook = post_request_hook
        self.reset()

    def reset(self):
        """
        Resets the state of the application; currently just clears
        saved cookies.
        """
        self.cookies = {}

    def _make_environ(self):
        environ = self.extra_environ.copy()
        environ['paste.throw_errors'] = True
        return environ

    def get(self, url, params=None, headers=None, extra_environ=None,
            status=None, expect_errors=False):
        """
        Get the given url (well, actually a path like
        ``'/page.html'``).

        ``params``:
            A query string, or a dictionary that will be encoded
            into a query string.  You may also include a query
            string on the ``url``.

        ``headers``:
            A dictionary of extra headers to send.

        ``extra_environ``:
            A dictionary of environmental variables that should
            be added to the request.

        ``status``:
            The integer status code you expect (if not 200 or 3xx).
            If you expect a 404 response, for instance, you must give
            ``status=404`` or it will be an error.  You can also give
            a wildcard, like ``'3*'`` or ``'*'``.

        ``expect_errors``:
            If this is not true, then if anything is written to
            ``wsgi.errors`` it will be an error.  If it is true, then
            non-200/3xx responses are also okay.

        Returns a `response object
        <class-paste.fixture.TestResponse.html>`_
        """
        if extra_environ is None:
            extra_environ = {}
        # Hide from py.test:
        __tracebackhide__ = True
        if params:
            if not isinstance(params, (str, unicode)):
                params = urllib.urlencode(params, doseq=True)
            if '?' in url:
                url += '&'
            else:
                url += '?'
            url += params
        environ = self._make_environ()
        url = str(url)
        if '?' in url:
            url, environ['QUERY_STRING'] = url.split('?', 1)
        else:
            environ['QUERY_STRING'] = ''
        self._set_headers(headers, environ)
        environ.update(extra_environ)
        req = TestRequest(url, environ, expect_errors)
        return self.do_request(req, status=status)

    def _gen_request(self, method, url, params='', headers=None, extra_environ=None,
             status=None, upload_files=None, expect_errors=False):
        """
        Do a generic request.
        """
        if headers is None:
            headers = {}
        if extra_environ is None:
            extra_environ = {}
        environ = self._make_environ()
        # @@: Should this be all non-strings?
        if isinstance(params, (list, tuple, dict)):
            params = urllib.urlencode(params)
        if hasattr(params, 'items'):
            # Some other multi-dict like format
            params = urllib.urlencode(params.items())
        if upload_files:
            params = cgi.parse_qsl(params, keep_blank_values=True)
            content_type, params = self.encode_multipart(
                params, upload_files)
            environ['CONTENT_TYPE'] = content_type
        elif params:
            environ.setdefault('CONTENT_TYPE', 'application/x-www-form-urlencoded')
        if '?' in url:
            url, environ['QUERY_STRING'] = url.split('?', 1)
        else:
            environ['QUERY_STRING'] = ''
        environ['CONTENT_LENGTH'] = str(len(params))
        environ['REQUEST_METHOD'] = method
        environ['wsgi.input'] = StringIO(params)
        self._set_headers(headers, environ)
        environ.update(extra_environ)
        req = TestRequest(url, environ, expect_errors)
        return self.do_request(req, status=status)

    def post(self, url, params='', headers=None, extra_environ=None,
             status=None, upload_files=None, expect_errors=False):
        """
        Do a POST request.  Very like the ``.get()`` method.
        ``params`` are put in the body of the request.

        ``upload_files`` is for file uploads.  It should be a list of
        ``[(fieldname, filename, file_content)]``.  You can also use
        just ``[(fieldname, filename)]`` and the file content will be
        read from disk.

        Returns a `response object
        <class-paste.fixture.TestResponse.html>`_
        """
        return self._gen_request('POST', url, params=params, headers=headers,
                                 extra_environ=extra_environ,status=status,
                                 upload_files=upload_files,
                                 expect_errors=expect_errors)

    def put(self, url, params='', headers=None, extra_environ=None,
             status=None, upload_files=None, expect_errors=False):
        """
        Do a PUT request.  Very like the ``.get()`` method.
        ``params`` are put in the body of the request.

        ``upload_files`` is for file uploads.  It should be a list of
        ``[(fieldname, filename, file_content)]``.  You can also use
        just ``[(fieldname, filename)]`` and the file content will be
        read from disk.

        Returns a `response object
        <class-paste.fixture.TestResponse.html>`_
        """
        return self._gen_request('PUT', url, params=params, headers=headers,
                                 extra_environ=extra_environ,status=status,
                                 upload_files=upload_files,
                                 expect_errors=expect_errors)

    def delete(self, url, params='', headers=None, extra_environ=None,
               status=None, expect_errors=False):
        """
        Do a DELETE request.  Very like the ``.get()`` method.
        ``params`` are put in the body of the request.

        Returns a `response object
        <class-paste.fixture.TestResponse.html>`_
        """
        return self._gen_request('DELETE', url, params=params, headers=headers,
                                 extra_environ=extra_environ,status=status,
                                 upload_files=None, expect_errors=expect_errors)




    def _set_headers(self, headers, environ):
        """
        Turn any headers into environ variables
        """
        if not headers:
            return
        for header, value in headers.items():
            if header.lower() == 'content-type':
                var = 'CONTENT_TYPE'
            elif header.lower() == 'content-length':
                var = 'CONTENT_LENGTH'
            else:
                var = 'HTTP_%s' % header.replace('-', '_').upper()
            environ[var] = value

    def encode_multipart(self, params, files):
        """
        Encodes a set of parameters (typically a name/value list) and
        a set of files (a list of (name, filename, file_body)) into a
        typical POST body, returning the (content_type, body).
        """
        boundary = '----------a_BoUnDaRy%s$' % random.random()
        lines = []
        for key, value in params:
            lines.append('--'+boundary)
            lines.append('Content-Disposition: form-data; name="%s"' % key)
            lines.append('')
            lines.append(value)
        for file_info in files:
            key, filename, value = self._get_file_info(file_info)
            lines.append('--'+boundary)
            lines.append('Content-Disposition: form-data; name="%s"; filename="%s"'
                         % (key, filename))
            fcontent = mimetypes.guess_type(filename)[0]
            lines.append('Content-Type: %s' %
                         fcontent or 'application/octet-stream')
            lines.append('')
            lines.append(value)
        lines.append('--' + boundary + '--')
        lines.append('')
        body = '\r\n'.join(lines)
        content_type = 'multipart/form-data; boundary=%s' % boundary
        return content_type, body

    def _get_file_info(self, file_info):
        if len(file_info) == 2:
            # It only has a filename
            filename = file_info[1]
            if self.relative_to:
                filename = os.path.join(self.relative_to, filename)
            f = open(filename, 'rb')
            content = f.read()
            f.close()
            return (file_info[0], filename, content)
        elif len(file_info) == 3:
            return file_info
        else:
            raise ValueError(
                "upload_files need to be a list of tuples of (fieldname, "
                "filename, filecontent) or (fieldname, filename); "
                "you gave: %r"
                % repr(file_info)[:100])

    def do_request(self, req, status):
        """
        Executes the given request (``req``), with the expected
        ``status``.  Generally ``.get()`` and ``.post()`` are used
        instead.
        """
        if self.pre_request_hook:
            self.pre_request_hook(self)
        __tracebackhide__ = True
        if self.cookies:
            c = BaseCookie()
            for name, value in self.cookies.items():
                c[name] = value
            hc = '; '.join(['='.join([m.key, m.value]) for m in c.values()])
            req.environ['HTTP_COOKIE'] = hc
        req.environ['paste.testing'] = True
        req.environ['paste.testing_variables'] = {}
        app = lint.middleware(self.app)
        old_stdout = sys.stdout
        out = CaptureStdout(old_stdout)
        try:
            sys.stdout = out
            start_time = time.time()
            raise_on_wsgi_error = not req.expect_errors
            raw_res = wsgilib.raw_interactive(
                app, req.url,
                raise_on_wsgi_error=raise_on_wsgi_error,
                **req.environ)
            end_time = time.time()
        finally:
            sys.stdout = old_stdout
            sys.stderr.write(out.getvalue())
        res = self._make_response(raw_res, end_time - start_time)
        res.request = req
        for name, value in req.environ['paste.testing_variables'].items():
            if hasattr(res, name):
                raise ValueError(
                    "paste.testing_variables contains the variable %r, but "
                    "the response object already has an attribute by that "
                    "name" % name)
            setattr(res, name, value)
        if self.namespace is not None:
            self.namespace['res'] = res
        if not req.expect_errors:
            self._check_status(status, res)
            self._check_errors(res)
        res.cookies_set = {}
        for header in res.all_headers('set-cookie'):
            c = BaseCookie(header)
            for key, morsel in c.items():
                self.cookies[key] = morsel.value
                res.cookies_set[key] = morsel.value
        if self.post_request_hook:
            self.post_request_hook(self)
        if self.namespace is None:
            # It's annoying to return the response in doctests, as it'll
            # be printed, so we only return it is we couldn't assign
            # it anywhere
            return res

    def _check_status(self, status, res):
        __tracebackhide__ = True
        if status == '*':
            return
        if isinstance(status, (list, tuple)):
            if res.status not in status:
                raise AppError(
                    "Bad response: %s (not one of %s for %s)\n%s"
                    % (res.full_status, ', '.join(map(str, status)),
                       res.request.url, res.body))
            return
        if status is None:
            if res.status >= 200 and res.status < 400:
                return
            raise AppError(
                "Bad response: %s (not 200 OK or 3xx redirect for %s)\n%s"
                % (res.full_status, res.request.url,
                   res.body))
        if status != res.status:
            raise AppError(
                "Bad response: %s (not %s)" % (res.full_status, status))

    def _check_errors(self, res):
        if res.errors:
            raise AppError(
                "Application had errors logged:\n%s" % res.errors)

    def _make_response(self, (status, headers, body, errors), total_time):
        return TestResponse(self, status, headers, body, errors,
                            total_time)

class CaptureStdout(object):

    def __init__(self, actual):
        self.captured = StringIO()
        self.actual = actual

    def write(self, s):
        self.captured.write(s)
        self.actual.write(s)

    def flush(self):
        self.actual.flush()

    def writelines(self, lines):
        for item in lines:
            self.write(item)

    def getvalue(self):
        return self.captured.getvalue()

class TestResponse(object):

    # for py.test
    disabled = True

    """
    Instances of this class are return by `TestApp
    <class-paste.fixture.TestApp.html>`_
    """

    def __init__(self, test_app, status, headers, body, errors,
                 total_time):
        self.test_app = test_app
        self.status = int(status.split()[0])
        self.full_status = status
        self.headers = headers
        self.header_dict = HeaderDict.fromlist(self.headers)
        self.body = body
        self.errors = errors
        self._normal_body = None
        self.time = total_time
        self._forms_indexed = None

    def forms__get(self):
        """
        Returns a dictionary of ``Form`` objects.  Indexes are both in
        order (from zero) and by form id (if the form is given an id).
        """
        if self._forms_indexed is None:
            self._parse_forms()
        return self._forms_indexed

    forms = property(forms__get,
                     doc="""
                     A list of <form>s found on the page (instances of
                     `Form <class-paste.fixture.Form.html>`_)
                     """)

    def form__get(self):
        forms = self.forms
        if not forms:
            raise TypeError(
                "You used response.form, but no forms exist")
        if 1 in forms:
            # There is more than one form
            raise TypeError(
                "You used response.form, but more than one form exists")
        return forms[0]

    form = property(form__get,
                    doc="""
                    Returns a single `Form
                    <class-paste.fixture.Form.html>`_ instance; it
                    is an error if there are multiple forms on the
                    page.
                    """)

    _tag_re = re.compile(r'<(/?)([:a-z0-9_\-]*)(.*?)>', re.S|re.I)

    def _parse_forms(self):
        forms = self._forms_indexed = {}
        form_texts = []
        started = None
        for match in self._tag_re.finditer(self.body):
            end = match.group(1) == '/'
            tag = match.group(2).lower()
            if tag != 'form':
                continue
            if end:
                assert started, (
                    "</form> unexpected at %s" % match.start())
                form_texts.append(self.body[started:match.end()])
                started = None
            else:
                assert not started, (
                    "Nested form tags at %s" % match.start())
                started = match.start()
        assert not started, (
            "Danging form: %r" % self.body[started:])
        for i, text in enumerate(form_texts):
            form = Form(self, text)
            forms[i] = form
            if form.id:
                forms[form.id] = form

    def header(self, name, default=NoDefault):
        """
        Returns the named header; an error if there is not exactly one
        matching header (unless you give a default -- always an error
        if there is more than one header)
        """
        found = None
        for cur_name, value in self.headers:
            if cur_name.lower() == name.lower():
                assert not found, (
                    "Ambiguous header: %s matches %r and %r"
                    % (name, found, value))
                found = value
        if found is None:
            if default is NoDefault:
                raise KeyError(
                    "No header found: %r (from %s)"
                    % (name, ', '.join([n for n, v in self.headers])))
            else:
                return default
        return found

    def all_headers(self, name):
        """
        Gets all headers by the ``name``, returns as a list
        """
        found = []
        for cur_name, value in self.headers:
            if cur_name.lower() == name.lower():
                found.append(value)
        return found

    def follow(self, **kw):
        """
        If this request is a redirect, follow that redirect.  It
        is an error if this is not a redirect response.  Returns
        another response object.
        """
        assert self.status >= 300 and self.status < 400, (
            "You can only follow redirect responses (not %s)"
            % self.full_status)
        location = self.header('location')
        type, rest = urllib.splittype(location)
        host, path = urllib.splithost(rest)
        # @@: We should test that it's not a remote redirect
        return self.test_app.get(location, **kw)

    def click(self, description=None, linkid=None, href=None,
              anchor=None, index=None, verbose=False):
        """
        Click the link as described.  Each of ``description``,
        ``linkid``, and ``url`` are *patterns*, meaning that they are
        either strings (regular expressions), compiled regular
        expressions (objects with a ``search`` method), or callables
        returning true or false.

        All the given patterns are ANDed together:

        * ``description`` is a pattern that matches the contents of the
          anchor (HTML and all -- everything between ``<a...>`` and
          ``</a>``)

        * ``linkid`` is a pattern that matches the ``id`` attribute of
          the anchor.  It will receive the empty string if no id is
          given.

        * ``href`` is a pattern that matches the ``href`` of the anchor;
          the literal content of that attribute, not the fully qualified
          attribute.

        * ``anchor`` is a pattern that matches the entire anchor, with
          its contents.

        If more than one link matches, then the ``index`` link is
        followed.  If ``index`` is not given and more than one link
        matches, or if no link matches, then ``IndexError`` will be
        raised.

        If you give ``verbose`` then messages will be printed about
        each link, and why it does or doesn't match.  If you use
        ``app.click(verbose=True)`` you'll see a list of all the
        links.

        You can use multiple criteria to essentially assert multiple
        aspects about the link, e.g., where the link's destination is.
        """
        __tracebackhide__ = True
        found_html, found_desc, found_attrs = self._find_element(
            tag='a', href_attr='href',
            href_extract=None,
            content=description,
            id=linkid,
            href_pattern=href,
            html_pattern=anchor,
            index=index, verbose=verbose)
        return self.goto(found_attrs['uri'])

    def clickbutton(self, description=None, buttonid=None, href=None,
                    button=None, index=None, verbose=False):
        """
        Like ``.click()``, except looks for link-like buttons.
        This kind of button should look like
        ``<button onclick="...location.href='url'...">``.
        """
        __tracebackhide__ = True
        found_html, found_desc, found_attrs = self._find_element(
            tag='button', href_attr='onclick',
            href_extract=re.compile(r"location\.href='(.*?)'"),
            content=description,
            id=buttonid,
            href_pattern=href,
            html_pattern=button,
            index=index, verbose=verbose)
        return self.goto(found_attrs['uri'])

    def _find_element(self, tag, href_attr, href_extract,
                      content, id,
                      href_pattern,
                      html_pattern,
                      index, verbose):
        content_pat = _make_pattern(content)
        id_pat = _make_pattern(id)
        href_pat = _make_pattern(href_pattern)
        html_pat = _make_pattern(html_pattern)

        _tag_re = re.compile(r'<%s\s+(.*?)>(.*?)</%s>' % (tag, tag),
                             re.I+re.S)

        def printlog(s):
            if verbose:
                print s

        found_links = []
        total_links = 0
        for match in _tag_re.finditer(self.body):
            el_html = match.group(0)
            el_attr = match.group(1)
            el_content = match.group(2)
            attrs = _parse_attrs(el_attr)
            if verbose:
                printlog('Element: %r' % el_html)
            if not attrs.get(href_attr):
                printlog('  Skipped: no %s attribute' % href_attr)
                continue
            el_href = attrs[href_attr]
            if href_extract:
                m = href_extract.search(el_href)
                if not m:
                    printlog("  Skipped: doesn't match extract pattern")
                    continue
                el_href = m.group(1)
            attrs['uri'] = el_href
            if el_href.startswith('#'):
                printlog('  Skipped: only internal fragment href')
                continue
            if el_href.startswith('javascript:'):
                printlog('  Skipped: cannot follow javascript:')
                continue
            total_links += 1
            if content_pat and not content_pat(el_content):
                printlog("  Skipped: doesn't match description")
                continue
            if id_pat and not id_pat(attrs.get('id', '')):
                printlog("  Skipped: doesn't match id")
                continue
            if href_pat and not href_pat(el_href):
                printlog("  Skipped: doesn't match href")
                continue
            if html_pat and not html_pat(el_html):
                printlog("  Skipped: doesn't match html")
                continue
            printlog("  Accepted")
            found_links.append((el_html, el_content, attrs))
        if not found_links:
            raise IndexError(
                "No matching elements found (from %s possible)"
                % total_links)
        if index is None:
            if len(found_links) > 1:
                raise IndexError(
                    "Multiple links match: %s"
                    % ', '.join([repr(anc) for anc, d, attr in found_links]))
            found_link = found_links[0]
        else:
            try:
                found_link = found_links[index]
            except IndexError:
                raise IndexError(
                    "Only %s (out of %s) links match; index %s out of range"
                    % (len(found_links), total_links, index))
        return found_link

    def goto(self, href, method='get', **args):
        """
        Go to the (potentially relative) link ``href``, using the
        given method (``'get'`` or ``'post'``) and any extra arguments
        you want to pass to the ``app.get()`` or ``app.post()``
        methods.

        All hostnames and schemes will be ignored.
        """
        scheme, host, path, query, fragment = urlparse.urlsplit(href)
        # We
        scheme = host = fragment = ''
        href = urlparse.urlunsplit((scheme, host, path, query, fragment))
        href = urlparse.urljoin(self.request.full_url, href)
        method = method.lower()
        assert method in ('get', 'post'), (
            'Only "get" or "post" are allowed for method (you gave %r)'
            % method)
        if method == 'get':
            method = self.test_app.get
        else:
            method = self.test_app.post
        return method(href, **args)

    _normal_body_regex = re.compile(r'[ \n\r\t]+')

    def normal_body__get(self):
        if self._normal_body is None:
            self._normal_body = self._normal_body_regex.sub(
                ' ', self.body)
        return self._normal_body

    normal_body = property(normal_body__get,
                           doc="""
                           Return the whitespace-normalized body
                           """)

    def __contains__(self, s):
        """
        A response 'contains' a string if it is present in the body
        of the response.  Whitespace is normalized when searching
        for a string.
        """
        if not isinstance(s, (str, unicode)):
            s = str(s)
        if isinstance(s, unicode):
            ## FIXME: we don't know that this response uses utf8:
            s = s.encode('utf8')
        return (self.body.find(s) != -1
                or self.normal_body.find(s) != -1)

    def mustcontain(self, *strings, **kw):
        """
        Assert that the response contains all of the strings passed
        in as arguments.

        Equivalent to::

            assert string in res
        """
        if 'no' in kw:
            no = kw['no']
            del kw['no']
            if isinstance(no, basestring):
                no = [no]
        else:
            no = []
        if kw:
            raise TypeError(
                "The only keyword argument allowed is 'no'")
        for s in strings:
            if not s in self:
                print >> sys.stderr, "Actual response (no %r):" % s
                print >> sys.stderr, self
                raise IndexError(
                    "Body does not contain string %r" % s)
        for no_s in no:
            if no_s in self:
                print >> sys.stderr, "Actual response (has %r)" % no_s
                print >> sys.stderr, self
                raise IndexError(
                    "Body contains string %r" % s)

    def __repr__(self):
        return '<Response %s %r>' % (self.full_status, self.body[:20])

    def __str__(self):
        simple_body = '\n'.join([l for l in self.body.splitlines()
                                 if l.strip()])
        return 'Response: %s\n%s\n%s' % (
            self.status,
            '\n'.join(['%s: %s' % (n, v) for n, v in self.headers]),
            simple_body)

    def showbrowser(self):
        """
        Show this response in a browser window (for debugging purposes,
        when it's hard to read the HTML).
        """
        import webbrowser
        fn = tempnam_no_warning(None, 'paste-fixture') + '.html'
        f = open(fn, 'wb')
        f.write(self.body)
        f.close()
        url = 'file:' + fn.replace(os.sep, '/')
        webbrowser.open_new(url)

class TestRequest(object):

    # for py.test
    disabled = True

    """
    Instances of this class are created by `TestApp
    <class-paste.fixture.TestApp.html>`_ with the ``.get()`` and
    ``.post()`` methods, and are consumed there by ``.do_request()``.

    Instances are also available as a ``.req`` attribute on
    `TestResponse <class-paste.fixture.TestResponse.html>`_ instances.

    Useful attributes:

    ``url``:
        The url (actually usually the path) of the request, without
        query string.

    ``environ``:
        The environment dictionary used for the request.

    ``full_url``:
        The url/path, with query string.
    """

    def __init__(self, url, environ, expect_errors=False):
        if url.startswith('http://localhost'):
            url = url[len('http://localhost'):]
        self.url = url
        self.environ = environ
        if environ.get('QUERY_STRING'):
            self.full_url = url + '?' + environ['QUERY_STRING']
        else:
            self.full_url = url
        self.expect_errors = expect_errors


class Form(object):

    """
    This object represents a form that has been found in a page.
    This has a couple useful attributes:

    ``text``:
        the full HTML of the form.

    ``action``:
        the relative URI of the action.

    ``method``:
        the method (e.g., ``'GET'``).

    ``id``:
        the id, or None if not given.

    ``fields``:
        a dictionary of fields, each value is a list of fields by
        that name.  ``<input type=\"radio\">`` and ``<select>`` are
        both represented as single fields with multiple options.
    """

    # @@: This really should be using Mechanize/ClientForm or
    # something...

    _tag_re = re.compile(r'<(/?)([:a-z0-9_\-]*)([^>]*?)>', re.I)

    def __init__(self, response, text):
        self.response = response
        self.text = text
        self._parse_fields()
        self._parse_action()

    def _parse_fields(self):
        in_select = None
        in_textarea = None
        fields = {}
        for match in self._tag_re.finditer(self.text):
            end = match.group(1) == '/'
            tag = match.group(2).lower()
            if tag not in ('input', 'select', 'option', 'textarea',
                           'button'):
                continue
            if tag == 'select' and end:
                assert in_select, (
                    '%r without starting select' % match.group(0))
                in_select = None
                continue
            if tag == 'textarea' and end:
                assert in_textarea, (
                    "</textarea> with no <textarea> at %s" % match.start())
                in_textarea[0].value = html_unquote(self.text[in_textarea[1]:match.start()])
                in_textarea = None
                continue
            if end:
                continue
            attrs = _parse_attrs(match.group(3))
            if 'name' in attrs:
                name = attrs.pop('name')
            else:
                name = None
            if tag == 'option':
                in_select.options.append((attrs.get('value'),
                                          'selected' in attrs))
                continue
            if tag == 'input' and attrs.get('type') == 'radio':
                field = fields.get(name)
                if not field:
                    field = Radio(self, tag, name, match.start(), **attrs)
                    fields.setdefault(name, []).append(field)
                else:
                    field = field[0]
                    assert isinstance(field, Radio)
                field.options.append((attrs.get('value'),
                                      'checked' in attrs))
                continue
            tag_type = tag
            if tag == 'input':
                tag_type = attrs.get('type', 'text').lower()
            FieldClass = Field.classes.get(tag_type, Field)
            field = FieldClass(self, tag, name, match.start(), **attrs)
            if tag == 'textarea':
                assert not in_textarea, (
                    "Nested textareas: %r and %r"
                    % (in_textarea, match.group(0)))
                in_textarea = field, match.end()
            elif tag == 'select':
                assert not in_select, (
                    "Nested selects: %r and %r"
                    % (in_select, match.group(0)))
                in_select = field
            fields.setdefault(name, []).append(field)
        self.fields = fields

    def _parse_action(self):
        self.action = None
        for match in self._tag_re.finditer(self.text):
            end = match.group(1) == '/'
            tag = match.group(2).lower()
            if tag != 'form':
                continue
            if end:
                break
            attrs = _parse_attrs(match.group(3))
            self.action = attrs.get('action', '')
            self.method = attrs.get('method', 'GET')
            self.id = attrs.get('id')
            # @@: enctype?
        else:
            assert 0, "No </form> tag found"
        assert self.action is not None, (
            "No <form> tag found")

    def __setitem__(self, name, value):
        """
        Set the value of the named field.  If there is 0 or multiple
        fields by that name, it is an error.

        Setting the value of a ``<select>`` selects the given option
        (and confirms it is an option).  Setting radio fields does the
        same.  Checkboxes get boolean values.  You cannot set hidden
        fields or buttons.

        Use ``.set()`` if there is any ambiguity and you must provide
        an index.
        """
        fields = self.fields.get(name)
        assert fields is not None, (
            "No field by the name %r found (fields: %s)"
            % (name, ', '.join(map(repr, self.fields.keys()))))
        assert len(fields) == 1, (
            "Multiple fields match %r: %s"
            % (name, ', '.join(map(repr, fields))))
        fields[0].value = value

    def __getitem__(self, name):
        """
        Get the named field object (ambiguity is an error).
        """
        fields = self.fields.get(name)
        assert fields is not None, (
            "No field by the name %r found" % name)
        assert len(fields) == 1, (
            "Multiple fields match %r: %s"
            % (name, ', '.join(map(repr, fields))))
        return fields[0]

    def set(self, name, value, index=None):
        """
        Set the given name, using ``index`` to disambiguate.
        """
        if index is None:
            self[name] = value
        else:
            fields = self.fields.get(name)
            assert fields is not None, (
                "No fields found matching %r" % name)
            field = fields[index]
            field.value = value

    def get(self, name, index=None, default=NoDefault):
        """
        Get the named/indexed field object, or ``default`` if no field
        is found.
        """
        fields = self.fields.get(name)
        if fields is None and default is not NoDefault:
            return default
        if index is None:
            return self[name]
        else:
            fields = self.fields.get(name)
            assert fields is not None, (
                "No fields found matching %r" % name)
            field = fields[index]
            return field

    def select(self, name, value, index=None):
        """
        Like ``.set()``, except also confirms the target is a
        ``<select>``.
        """
        field = self.get(name, index=index)
        assert isinstance(field, Select)
        field.value = value

    def submit(self, name=None, index=None, **args):
        """
        Submits the form.  If ``name`` is given, then also select that
        button (using ``index`` to disambiguate)``.

        Any extra keyword arguments are passed to the ``.get()`` or
        ``.post()`` method.

        Returns a response object.
        """
        fields = self.submit_fields(name, index=index)
        return self.response.goto(self.action, method=self.method,
                                  params=fields, **args)

    def submit_fields(self, name=None, index=None):
        """
        Return a list of ``[(name, value), ...]`` for the current
        state of the form.
        """
        submit = []
        if name is not None:
            field = self.get(name, index=index)
            submit.append((field.name, field.value_if_submitted()))
        for name, fields in self.fields.items():
            if name is None:
                continue
            for field in fields:
                value = field.value
                if value is None:
                    continue
                submit.append((name, value))
        return submit


_attr_re = re.compile(r'([^= \n\r\t]+)[ \n\r\t]*(?:=[ \n\r\t]*(?:"([^"]*)"|([^"][^ \n\r\t>]*)))?', re.S)

def _parse_attrs(text):
    attrs = {}
    for match in _attr_re.finditer(text):
        attr_name = match.group(1).lower()
        attr_body = match.group(2) or match.group(3)
        attr_body = html_unquote(attr_body or '')
        attrs[attr_name] = attr_body
    return attrs

class Field(object):

    """
    Field object.
    """

    # Dictionary of field types (select, radio, etc) to classes
    classes = {}

    settable = True

    def __init__(self, form, tag, name, pos,
                 value=None, id=None, **attrs):
        self.form = form
        self.tag = tag
        self.name = name
        self.pos = pos
        self._value = value
        self.id = id
        self.attrs = attrs

    def value__set(self, value):
        if not self.settable:
            raise AttributeError(
                "You cannot set the value of the <%s> field %r"
                % (self.tag, self.name))
        self._value = value

    def force_value(self, value):
        """
        Like setting a value, except forces it even for, say, hidden
        fields.
        """
        self._value = value

    def value__get(self):
        return self._value

    value = property(value__get, value__set)

class Select(Field):

    """
    Field representing ``<select>``
    """

    def __init__(self, *args, **attrs):
        super(Select, self).__init__(*args, **attrs)
        self.options = []
        self.multiple = attrs.get('multiple')
        assert not self.multiple, (
            "<select multiple> not yet supported")
        # Undetermined yet:
        self.selectedIndex = None

    def value__set(self, value):
        for i, (option, checked) in enumerate(self.options):
            if option == str(value):
                self.selectedIndex = i
                break
        else:
            raise ValueError(
                "Option %r not found (from %s)"
                % (value, ', '.join(
                [repr(o) for o, c in self.options])))

    def value__get(self):
        if self.selectedIndex is not None:
            return self.options[self.selectedIndex][0]
        else:
            for option, checked in self.options:
                if checked:
                    return option
            else:
                if self.options:
                    return self.options[0][0]
                else:
                    return None

    value = property(value__get, value__set)

Field.classes['select'] = Select

class Radio(Select):

    """
    Field representing ``<input type="radio">``
    """

Field.classes['radio'] = Radio

class Checkbox(Field):

    """
    Field representing ``<input type="checkbox">``
    """

    def __init__(self, *args, **attrs):
        super(Checkbox, self).__init__(*args, **attrs)
        self.checked = 'checked' in attrs

    def value__set(self, value):
        self.checked = not not value

    def value__get(self):
        if self.checked:
            if self._value is None:
                return 'on'
            else:
                return self._value
        else:
            return None

    value = property(value__get, value__set)

Field.classes['checkbox'] = Checkbox

class Text(Field):
    """
    Field representing ``<input type="text">``
    """
    def __init__(self, form, tag, name, pos,
                 value='', id=None, **attrs):
        #text fields default to empty string
        Field.__init__(self, form, tag, name, pos,
                       value=value, id=id, **attrs)

Field.classes['text'] = Text

class Textarea(Text):
    """
    Field representing ``<textarea>``
    """

Field.classes['textarea'] = Textarea

class Hidden(Text):
    """
    Field representing ``<input type="hidden">``
    """

Field.classes['hidden'] = Hidden

class Submit(Field):
    """
    Field representing ``<input type="submit">`` and ``<button>``
    """

    settable = False

    def value__get(self):
        return None

    value = property(value__get)

    def value_if_submitted(self):
        return self._value

Field.classes['submit'] = Submit

Field.classes['button'] = Submit

Field.classes['image'] = Submit

############################################################
## Command-line testing
############################################################


class TestFileEnvironment(object):

    """
    This represents an environment in which files will be written, and
    scripts will be run.
    """

    # for py.test
    disabled = True

    def __init__(self, base_path, template_path=None,
                 script_path=None,
                 environ=None, cwd=None, start_clear=True,
                 ignore_paths=None, ignore_hidden=True):
        """
        Creates an environment.  ``base_path`` is used as the current
        working directory, and generally where changes are looked for.

        ``template_path`` is the directory to look for *template*
        files, which are files you'll explicitly add to the
        environment.  This is done with ``.writefile()``.

        ``script_path`` is the PATH for finding executables.  Usually
        grabbed from ``$PATH``.

        ``environ`` is the operating system environment,
        ``os.environ`` if not given.

        ``cwd`` is the working directory, ``base_path`` by default.

        If ``start_clear`` is true (default) then the ``base_path``
        will be cleared (all files deleted) when an instance is
        created.  You can also use ``.clear()`` to clear the files.

        ``ignore_paths`` is a set of specific filenames that should be
        ignored when created in the environment.  ``ignore_hidden``
        means, if true (default) that filenames and directories
        starting with ``'.'`` will be ignored.
        """
        self.base_path = base_path
        self.template_path = template_path
        if environ is None:
            environ = os.environ.copy()
        self.environ = environ
        if script_path is None:
            if sys.platform == 'win32':
                script_path = environ.get('PATH', '').split(';')
            else:
                script_path = environ.get('PATH', '').split(':')
        self.script_path = script_path
        if cwd is None:
            cwd = base_path
        self.cwd = cwd
        if start_clear:
            self.clear()
        elif not os.path.exists(base_path):
            os.makedirs(base_path)
        self.ignore_paths = ignore_paths or []
        self.ignore_hidden = ignore_hidden

    def run(self, script, *args, **kw):
        """
        Run the command, with the given arguments.  The ``script``
        argument can have space-separated arguments, or you can use
        the positional arguments.

        Keywords allowed are:

        ``expect_error``: (default False)
            Don't raise an exception in case of errors
        ``expect_stderr``: (default ``expect_error``)
            Don't raise an exception if anything is printed to stderr
        ``stdin``: (default ``""``)
            Input to the script
        ``printresult``: (default True)
            Print the result after running
        ``cwd``: (default ``self.cwd``)
            The working directory to run in

        Returns a `ProcResponse
        <class-paste.fixture.ProcResponse.html>`_ object.
        """
        __tracebackhide__ = True
        expect_error = _popget(kw, 'expect_error', False)
        expect_stderr = _popget(kw, 'expect_stderr', expect_error)
        cwd = _popget(kw, 'cwd', self.cwd)
        stdin = _popget(kw, 'stdin', None)
        printresult = _popget(kw, 'printresult', True)
        args = map(str, args)
        assert not kw, (
            "Arguments not expected: %s" % ', '.join(kw.keys()))
        if ' ' in script:
            assert not args, (
                "You cannot give a multi-argument script (%r) "
                "and arguments (%s)" % (script, args))
            script, args = script.split(None, 1)
            args = shlex.split(args)
        script = self._find_exe(script)
        all = [script] + args
        files_before = self._find_files()
        proc = subprocess.Popen(all, stdin=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                cwd=cwd,
                                env=self.environ)
        stdout, stderr = proc.communicate(stdin)
        files_after = self._find_files()
        result = ProcResult(
            self, all, stdin, stdout, stderr,
            returncode=proc.returncode,
            files_before=files_before,
            files_after=files_after)
        if printresult:
            print result
            print '-'*40
        if not expect_error:
            result.assert_no_error()
        if not expect_stderr:
            result.assert_no_stderr()
        return result

    def _find_exe(self, script_name):
        if self.script_path is None:
            script_name = os.path.join(self.cwd, script_name)
            if not os.path.exists(script_name):
                raise OSError(
                    "Script %s does not exist" % script_name)
            return script_name
        for path in self.script_path:
            fn = os.path.join(path, script_name)
            if os.path.exists(fn):
                return fn
        raise OSError(
            "Script %s could not be found in %s"
            % (script_name, ':'.join(self.script_path)))

    def _find_files(self):
        result = {}
        for fn in os.listdir(self.base_path):
            if self._ignore_file(fn):
                continue
            self._find_traverse(fn, result)
        return result

    def _ignore_file(self, fn):
        if fn in self.ignore_paths:
            return True
        if self.ignore_hidden and os.path.basename(fn).startswith('.'):
            return True
        return False

    def _find_traverse(self, path, result):
        full = os.path.join(self.base_path, path)
        if os.path.isdir(full):
            result[path] = FoundDir(self.base_path, path)
            for fn in os.listdir(full):
                fn = os.path.join(path, fn)
                if self._ignore_file(fn):
                    continue
                self._find_traverse(fn, result)
        else:
            result[path] = FoundFile(self.base_path, path)

    def clear(self):
        """
        Delete all the files in the base directory.
        """
        if os.path.exists(self.base_path):
            shutil.rmtree(self.base_path)
        os.mkdir(self.base_path)

    def writefile(self, path, content=None,
                  frompath=None):
        """
        Write a file to the given path.  If ``content`` is given then
        that text is written, otherwise the file in ``frompath`` is
        used.  ``frompath`` is relative to ``self.template_path``
        """
        full = os.path.join(self.base_path, path)
        if not os.path.exists(os.path.dirname(full)):
            os.makedirs(os.path.dirname(full))
        f = open(full, 'wb')
        if content is not None:
            f.write(content)
        if frompath is not None:
            if self.template_path:
                frompath = os.path.join(self.template_path, frompath)
            f2 = open(frompath, 'rb')
            f.write(f2.read())
            f2.close()
        f.close()
        return FoundFile(self.base_path, path)

class ProcResult(object):

    """
    Represents the results of running a command in
    `TestFileEnvironment
    <class-paste.fixture.TestFileEnvironment.html>`_.

    Attributes to pay particular attention to:

    ``stdout``, ``stderr``:
        What is produced

    ``files_created``, ``files_deleted``, ``files_updated``:
        Dictionaries mapping filenames (relative to the ``base_dir``)
        to `FoundFile <class-paste.fixture.FoundFile.html>`_ or
        `FoundDir <class-paste.fixture.FoundDir.html>`_ objects.
    """

    def __init__(self, test_env, args, stdin, stdout, stderr,
                 returncode, files_before, files_after):
        self.test_env = test_env
        self.args = args
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.files_before = files_before
        self.files_after = files_after
        self.files_deleted = {}
        self.files_updated = {}
        self.files_created = files_after.copy()
        for path, f in files_before.items():
            if path not in files_after:
                self.files_deleted[path] = f
                continue
            del self.files_created[path]
            if f.mtime < files_after[path].mtime:
                self.files_updated[path] = files_after[path]

    def assert_no_error(self):
        __tracebackhide__ = True
        assert self.returncode == 0, (
            "Script returned code: %s" % self.returncode)

    def assert_no_stderr(self):
        __tracebackhide__ = True
        if self.stderr:
            print 'Error output:'
            print self.stderr
            raise AssertionError("stderr output not expected")

    def __str__(self):
        s = ['Script result: %s' % ' '.join(self.args)]
        if self.returncode:
            s.append('  return code: %s' % self.returncode)
        if self.stderr:
            s.append('-- stderr: --------------------')
            s.append(self.stderr)
        if self.stdout:
            s.append('-- stdout: --------------------')
            s.append(self.stdout)
        for name, files, show_size in [
            ('created', self.files_created, True),
            ('deleted', self.files_deleted, True),
            ('updated', self.files_updated, True)]:
            if files:
                s.append('-- %s: -------------------' % name)
                files = files.items()
                files.sort()
                last = ''
                for path, f in files:
                    t = '  %s' % _space_prefix(last, path, indent=4,
                                               include_sep=False)
                    last = path
                    if show_size and f.size != 'N/A':
                        t += '  (%s bytes)' % f.size
                    s.append(t)
        return '\n'.join(s)

class FoundFile(object):

    """
    Represents a single file found as the result of a command.

    Has attributes:

    ``path``:
        The path of the file, relative to the ``base_path``

    ``full``:
        The full path

    ``stat``:
        The results of ``os.stat``.  Also ``mtime`` and ``size``
        contain the ``.st_mtime`` and ``st_size`` of the stat.

    ``bytes``:
        The contents of the file.

    You may use the ``in`` operator with these objects (tested against
    the contents of the file), and the ``.mustcontain()`` method.
    """

    file = True
    dir = False

    def __init__(self, base_path, path):
        self.base_path = base_path
        self.path = path
        self.full = os.path.join(base_path, path)
        self.stat = os.stat(self.full)
        self.mtime = self.stat.st_mtime
        self.size = self.stat.st_size
        self._bytes = None

    def bytes__get(self):
        if self._bytes is None:
            f = open(self.full, 'rb')
            self._bytes = f.read()
            f.close()
        return self._bytes
    bytes = property(bytes__get)

    def __contains__(self, s):
        return s in self.bytes

    def mustcontain(self, s):
        __tracebackhide__ = True
        bytes = self.bytes
        if s not in bytes:
            print 'Could not find %r in:' % s
            print bytes
            assert s in bytes

    def __repr__(self):
        return '<%s %s:%s>' % (
            self.__class__.__name__,
            self.base_path, self.path)

class FoundDir(object):

    """
    Represents a directory created by a command.
    """

    file = False
    dir = True

    def __init__(self, base_path, path):
        self.base_path = base_path
        self.path = path
        self.full = os.path.join(base_path, path)
        self.size = 'N/A'
        self.mtime = 'N/A'

    def __repr__(self):
        return '<%s %s:%s>' % (
            self.__class__.__name__,
            self.base_path, self.path)

def _popget(d, key, default=None):
    """
    Pop the key if found (else return default)
    """
    if key in d:
        return d.pop(key)
    return default

def _space_prefix(pref, full, sep=None, indent=None, include_sep=True):
    """
    Anything shared by pref and full will be replaced with spaces
    in full, and full returned.
    """
    if sep is None:
        sep = os.path.sep
    pref = pref.split(sep)
    full = full.split(sep)
    padding = []
    while pref and full and pref[0] == full[0]:
        if indent is None:
            padding.append(' ' * (len(full[0]) + len(sep)))
        else:
            padding.append(' ' * indent)
        full.pop(0)
        pref.pop(0)
    if padding:
        if include_sep:
            return ''.join(padding) + sep + sep.join(full)
        else:
            return ''.join(padding) + sep.join(full)
    else:
        return sep.join(full)

def _make_pattern(pat):
    if pat is None:
        return None
    if isinstance(pat, (str, unicode)):
        pat = re.compile(pat)
    if hasattr(pat, 'search'):
        return pat.search
    if callable(pat):
        return pat
    assert 0, (
        "Cannot make callable pattern object out of %r" % pat)

def setup_module(module=None):
    """
    This is used by py.test if it is in the module, so you can
    import this directly.

    Use like::

        from paste.fixture import setup_module
    """
    # Deprecated June 2008
    import warnings
    warnings.warn(
        'setup_module is deprecated',
        DeprecationWarning, 2)
    if module is None:
        # The module we were called from must be the module...
        module = sys._getframe().f_back.f_globals['__name__']
    if isinstance(module, (str, unicode)):
        module = sys.modules[module]
    if hasattr(module, 'reset_state'):
        module.reset_state()

def html_unquote(v):
    """
    Unquote (some) entities in HTML.  (incomplete)
    """
    for ent, repl in [('&nbsp;', ' '), ('&gt;', '>'),
                      ('&lt;', '<'), ('&quot;', '"'),
                      ('&amp;', '&')]:
        v = v.replace(ent, repl)
    return v
