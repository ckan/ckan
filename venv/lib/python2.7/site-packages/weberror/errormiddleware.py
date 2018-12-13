# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

"""
Error handler middleware
"""
import sys
import traceback
import cgi
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from weberror import formatter, collector, reporter
from paste import wsgilib
from paste import request
from paste.util import import_string
import types

__all__ = ['ErrorMiddleware', 'handle_exception']

class _NoDefault(object):
    def __repr__(self):
        return '<NoDefault>'
NoDefault = _NoDefault()

class ErrorMiddleware(object):

    """
    Error handling middleware
    
    Usage::

        error_catching_wsgi_app = ErrorMiddleware(wsgi_app)

    Settings:

      ``debug``:
          If true, then tracebacks will be shown in the browser.

      ``error_email``:
          an email address (or list of addresses) to send exception 
          reports to

      ``error_log``:
          a filename to append tracebacks to

      ``show_exceptions_in_wsgi_errors``:
          If true, then errors will be printed to ``wsgi.errors`` 
          (frequently a server error log, or stderr).

      ``from_address``, ``smtp_server``, ``error_subject_prefix``, ``smtp_username``, ``smtp_password``, ``smtp_use_tls``:
          variables to control the emailed exception reports

      ``error_message``:
          When debug mode is off, the error message to show to users.

      ``xmlhttp_key``:
          When this key (default ``_``) is in the request GET variables
          (not POST!), expect that this is an XMLHttpRequest, and the
          response should be more minimal; it should not be a complete
          HTML page.

      `show_error_reason``:
          If set to true and when debug mode is off,
          exception_type and exception_value are posted after error_message.

    Environment Configuration:
    
      ``paste.throw_errors``:
          If this setting in the request environment is true, then this
          middleware is disabled. This can be useful in a testing situation
          where you don't want errors to be caught and transformed.

      ``paste.expected_exceptions``:
          When this middleware encounters an exception listed in this
          environment variable and when the ``start_response`` has not 
          yet occurred, the exception will be re-raised instead of being
          caught.  This should generally be set by middleware that may 
          (but probably shouldn't be) installed above this middleware, 
          and wants to get certain exceptions.  Exceptions raised after
          ``start_response`` have been called are always caught since
          by definition they are no longer expected.

    """

    def __init__(self, application, global_conf=None,
                 debug=NoDefault,
                 error_email=None,
                 error_log=None,
                 show_exceptions_in_wsgi_errors=NoDefault,
                 from_address=None,
                 smtp_server=None,
                 smtp_username=None,
                 smtp_password=None,
                 smtp_use_tls=False,
                 error_subject_prefix=None,
                 error_message=None,
                 xmlhttp_key=None,
                 reporters=None,
                 show_error_reason=None):
        from paste.util import converters
        self.application = application
        # @@: global_conf should be handled elsewhere in a separate
        # function for the entry point
        if global_conf is None:
            global_conf = {}
        if debug is NoDefault:
            debug = converters.asbool(global_conf.get('debug'))
        if show_exceptions_in_wsgi_errors is NoDefault:
            show_exceptions_in_wsgi_errors = converters.asbool(global_conf.get('show_exceptions_in_wsgi_errors'))
        self.debug_mode = converters.asbool(debug)
        if error_email is None:
            error_email = (global_conf.get('error_email')
                           or global_conf.get('admin_email')
                           or global_conf.get('webmaster_email')
                           or global_conf.get('sysadmin_email'))
        self.error_email = converters.aslist(error_email)
        self.error_log = error_log
        self.show_exceptions_in_wsgi_errors = show_exceptions_in_wsgi_errors
        if from_address is None:
            from_address = global_conf.get('error_from_address')
            if from_address is None:
                if self.error_email:
                    from_address = self.error_email[0]
                else:
                    from_address = 'errors@localhost'
        self.from_address = from_address
        if smtp_server is None:
            smtp_server = global_conf.get('smtp_server', 'localhost')
        self.smtp_server = smtp_server
        self.smtp_username = smtp_username or global_conf.get('smtp_username')
        self.smtp_password = smtp_password or global_conf.get('smtp_password')
        self.smtp_use_tls = smtp_use_tls or converters.asbool(global_conf.get('smtp_use_tls'))
        self.error_subject_prefix = error_subject_prefix or ''
        if error_message is None:
            error_message = global_conf.get('error_message')
        self.error_message = error_message
        if xmlhttp_key is None:
            xmlhttp_key = global_conf.get('xmlhttp_key', '_')
        self.xmlhttp_key = xmlhttp_key
        reporters = reporters or global_conf.get('error_reporters')
        if reporters and isinstance(reporters, basestring):
            reporter_strings = reporters.split()
            reporters = []
            for reporter_string in reporter_strings:
                reporter = import_string.eval_import(reporter_string)
                if isinstance(reporter, (type, types.ClassType)):
                    reporter = reporter()
                reporters.append(reporter)
        self.reporters = reporters or []

        if show_error_reason is None:
            show_error_reason = global_conf.get('show_error_reason')
        self.show_error_reason = converters.asbool(show_error_reason)

    def __call__(self, environ, start_response):
        """
        The WSGI application interface.
        """
        # We want to be careful about not sending headers twice,
        # and the content type that the app has committed to (if there
        # is an exception in the iterator body of the response)
        if environ.get('paste.throw_errors'):
            return self.application(environ, start_response)
        environ['paste.throw_errors'] = True

        try:
            __traceback_supplement__ = Supplement, self, environ
            sr_checker = ResponseStartChecker(start_response)
            app_iter = self.application(environ, sr_checker)
            return self.make_catching_iter(app_iter, environ, sr_checker)
        except:
            exc_info = sys.exc_info()
            try:
                start_response('500 Internal Server Error',
                               [('content-type', 'text/html; charset=utf8')],
                               exc_info)
                # @@: it would be nice to deal with bad content types here
                response = self.exception_handler(exc_info, environ)
                if isinstance(response, unicode):
                    response = response.encode('utf8')
                return [response]
            finally:
                # clean up locals...
                exc_info = None

    def make_catching_iter(self, app_iter, environ, sr_checker):
        if isinstance(app_iter, (list, tuple)):
            # These don't raise
            return app_iter
        return CatchingIter(app_iter, environ, sr_checker, self)

    def exception_handler(self, exc_info, environ):
        simple_html_error = False
        if self.xmlhttp_key:
            get_vars = wsgilib.parse_querystring(environ)
            if dict(get_vars).get(self.xmlhttp_key):
                simple_html_error = True
        return handle_exception(
            exc_info, environ['wsgi.errors'],
            html=True,
            debug_mode=self.debug_mode,
            error_email=self.error_email,
            error_log=self.error_log,
            show_exceptions_in_wsgi_errors=self.show_exceptions_in_wsgi_errors,
            error_email_from=self.from_address,
            smtp_server=self.smtp_server,
            smtp_username=self.smtp_username,
            smtp_password=self.smtp_password,
            smtp_use_tls=self.smtp_use_tls,
            error_subject_prefix=self.error_subject_prefix,
            error_message=self.error_message,
            simple_html_error=simple_html_error,
            reporters=self.reporters,
            show_error_reason=self.show_error_reason)

class ResponseStartChecker(object):
    def __init__(self, start_response):
        self.start_response = start_response
        self.response_started = False

    def __call__(self, *args):
        self.response_started = True
        self.start_response(*args)

class CatchingIter(object):

    """
    A wrapper around the application iterator that will catch
    exceptions raised by the a generator, or by the close method, and
    display or report as necessary.
    """

    def __init__(self, app_iter, environ, start_checker, error_middleware):
        self.app_iterable = app_iter
        self.app_iterator = iter(app_iter)
        self.environ = environ
        self.start_checker = start_checker
        self.error_middleware = error_middleware
        self.closed = False

    def __iter__(self):
        return self

    def next(self):
        __traceback_supplement__ = (
            Supplement, self.error_middleware, self.environ)
        if self.closed:
            raise StopIteration
        try:
            return self.app_iterator.next()
        except StopIteration:
            self.closed = True
            close_response = self._close()
            if close_response is not None:
                return close_response
            else:
                raise StopIteration
        except:
            self.closed = True
            close_response = self._close()
            exc_info = sys.exc_info()
            response = self.error_middleware.exception_handler(
                exc_info, self.environ)
            if close_response is not None:
                response += (
                    '<hr noshade>Error in .close():<br>%s'
                    % close_response)

            if not self.start_checker.response_started:
                self.start_checker('500 Internal Server Error',
                               [('content-type', 'text/html')],
                               exc_info)

            return response

    def close(self):
        # This should at least print something to stderr if the
        # close method fails at this point
        if not self.closed:
            self._close()

    def _close(self):
        """Close and return any error message"""
        if not hasattr(self.app_iterable, 'close'):
            return None
        try:
            self.app_iterable.close()
            return None
        except:
            close_response = self.error_middleware.exception_handler(
                sys.exc_info(), self.environ)
            return close_response


class Supplement(object):
    """This is a supplement used to display standard WSGI information 
    in the traceback.
    
    Additional configuration information can be added under a 
    Configuration section by populating the environ['weberror.config']
    variable with a dictionary to include.
    
    """
    def __init__(self, middleware, environ):
        self.middleware = middleware
        self.environ = environ
        self.source_url = request.construct_url(environ)

    def extraData(self):
        data = {}
        cgi_vars = data[('extra', 'CGI Variables')] = {}
        wsgi_vars = data[('extra', 'WSGI Variables')] = {}
        hide_vars = ['paste.config', 'wsgi.errors', 'wsgi.input',
                     'wsgi.multithread', 'wsgi.multiprocess',
                     'wsgi.run_once', 'wsgi.version',
                     'wsgi.url_scheme']
        for name, value in self.environ.items():
            if name.upper() == name:
                if value:
                    cgi_vars[name] = value
            elif name not in hide_vars:
                wsgi_vars[name] = value
        if self.environ['wsgi.version'] != (1, 0):
            wsgi_vars['wsgi.version'] = self.environ['wsgi.version']
        proc_desc = tuple([int(bool(self.environ[key]))
                           for key in ('wsgi.multiprocess',
                                       'wsgi.multithread',
                                       'wsgi.run_once')])
        wsgi_vars['wsgi process'] = self.process_combos[proc_desc]
        wsgi_vars['application'] = self.middleware.application
        if 'weberror.config' in self.environ:
            data[('extra', 'Configuration')] = dict(self.environ['weberror.config'])
        return data

    process_combos = {
        # multiprocess, multithread, run_once
        (0, 0, 0): 'Non-concurrent server',
        (0, 1, 0): 'Multithreaded',
        (1, 0, 0): 'Multiprocess',
        (1, 1, 0): 'Multi process AND threads (?)',
        (0, 0, 1): 'Non-concurrent CGI',
        (0, 1, 1): 'Multithread CGI (?)',
        (1, 0, 1): 'CGI',
        (1, 1, 1): 'Multi thread/process CGI (?)',
        }
    
def handle_exception(exc_info, error_stream, html=True,
                     debug_mode=False,
                     error_email=None,
                     error_log=None,
                     show_exceptions_in_wsgi_errors=False,
                     error_email_from='errors@localhost',
                     smtp_server='localhost',
                     smtp_username=None, 
                     smtp_password=None, 
                     smtp_use_tls=False,
                     error_subject_prefix='',
                     error_message=None,
                     simple_html_error=False,
                     reporters=None,
                     show_error_reason=False
                     ):
    """
    For exception handling outside of a web context

    Use like::

        import sys
        import paste
        import paste.error_middleware
        try:
            do stuff
        except:
            paste.error_middleware.exception_handler(
                sys.exc_info(), paste.CONFIG, sys.stderr, html=False)

    If you want to report, but not fully catch the exception, call
    ``raise`` after ``exception_handler``, which (when given no argument)
    will reraise the exception.
    """
    reported = False
    exc_data = collector.collect_exception(*exc_info)
    extra_data = ''
    if error_email:
        rep = reporter.EmailReporter(
            to_addresses=error_email,
            from_address=error_email_from,
            smtp_server=smtp_server,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            smtp_use_tls=smtp_use_tls,
            subject_prefix=error_subject_prefix)
        rep_err = send_report(rep, exc_data, html=html)
        if rep_err:
            extra_data += rep_err
        else:
            reported = True
    if reporters:
        for rep in reporters:
            rep_err = send_report(rep, exc_data, html=html)
            if rep_err:
                extra_data += rep_err
            else:
                ## FIXME: should this be true?
                reported = True
    if error_log:
        rep = reporter.LogReporter(
            filename=error_log)
        rep_err = send_report(rep, exc_data, html=html)
        if rep_err:
            extra_data += rep_err
        else:
            reported = True
    if show_exceptions_in_wsgi_errors:
        rep = reporter.FileReporter(
            file=error_stream)
        rep_err = send_report(rep, exc_data, html=html)
        if rep_err:
            extra_data += rep_err
        else:
            reported = True
    else:
        error_stream.write('Error - %s: %s\n' % (
            exc_data.exception_type, exc_data.exception_value))
    if html:
        if debug_mode and simple_html_error:
            return_error = formatter.format_html(
                exc_data, include_hidden_frames=False,
                include_reusable=False, show_extra_data=False)
            reported = True
        elif debug_mode and not simple_html_error:
            error_html = formatter.format_html(
                exc_data,
                include_hidden_frames=True,
                include_reusable=False)
            head_html = ''
            return_error = error_template(
                head_html, error_html, extra_data)
            extra_data = ''
            reported = True
        else:
            default_msg = '''
            An error occurred.  See the error logs for more information.
            '''
            if not show_error_reason:
                default_msg += '''(Turn debug on to display exception reports here)'''

            msg = error_message or default_msg

            if show_error_reason:
                extra = "%s - %s" % (exc_data.exception_type, exc_data.exception_value)
                extra = cgi.escape(extra).encode('ascii', 'xmlcharrefreplace')
            else:
                extra = ''

            return_error = error_template('', msg, extra)
    else:
        return_error = None
    if not reported and error_stream:
        err_report = formatter.format_text(exc_data, show_hidden_frames=True)[0]
        err_report += '\n' + '-'*60 + '\n'
        error_stream.write(err_report)
    if extra_data:
        error_stream.write(extra_data)
    return return_error

def send_report(rep, exc_data, html=True):
    try:
        rep.report(exc_data)
    except:
        output = StringIO()
        traceback.print_exc(file=output)
        if html:
            return """
            <p>Additionally an error occurred while sending the %s report:

            <pre>%s</pre>
            </p>""" % (
                cgi.escape(str(rep)), output.getvalue())
        else:
            return (
                "Additionally an error occurred while sending the "
                "%s report:\n%s" % (str(rep), output.getvalue()))
    else:
        return ''

def error_template(head_html, exception, extra):
    return '''
    <html>
    <head>
    <title>Server Error</title>
    %s
    </head>
    <body>
    <h1>Server Error</h1>
    %s
    %s
    </body>
    </html>''' % (head_html, exception, extra)

def make_error_middleware(app, global_conf, **kw):
    return ErrorMiddleware(app, global_conf=global_conf, **kw)

doc_lines = (ErrorMiddleware.__doc__ or '').splitlines(True)
for i in range(len(doc_lines)):
    if doc_lines[i].strip().startswith('Settings'):
        make_error_middleware.__doc__ = ''.join(doc_lines[i:])
        break
del i, doc_lines
