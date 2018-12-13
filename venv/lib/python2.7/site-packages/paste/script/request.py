# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
import os
import re
import sys
import six
from six.moves.urllib.parse import quote, urljoin

from .command import Command, BadCommand
from paste.deploy import loadapp
from paste.wsgilib import raw_interactive

class RequestCommand(Command):

    min_args = 2
    usage = 'CONFIG_FILE URL [OPTIONS/ARGUMENTS]'
    takes_config_file = 1
    summary = "Run a request for the described application"
    description = """\
    This command makes an artifical request to a web application that
    uses a paste.deploy configuration file for the server and
    application.

    Use 'paster request config.ini /url' to request /url.  Use
    'paster post config.ini /url < data' to do a POST with the given
    request body.

    If the URL is relative (doesn't begin with /) it is interpreted as
    relative to /.command/.  The variable environ['paste.command_request']
    will be set to True in the request, so your application can distinguish
    these calls from normal requests.

    Note that you can pass options besides the options listed here; any unknown
    options will be passed to the application in environ['QUERY_STRING'].
    """

    parser = Command.standard_parser(quiet=True)
    parser.add_option('-n', '--app-name',
                      dest='app_name',
                      metavar='NAME',
                      help="Load the named application (default main)")
    parser.add_option('--config-var',
                      dest='config_vars',
                      metavar='NAME:VALUE',
                      action='append',
                      help="Variable to make available in the config for %()s substitution "
                      "(you can use this option multiple times)")
    parser.add_option('--header',
                      dest='headers',
                      metavar='NAME:VALUE',
                      action='append',
                      help="Header to add to request (you can use this option multiple times)")
    parser.add_option('--display-headers',
                      dest='display_headers',
                      action='store_true',
                      help='Display headers before the response body')

    ARG_OPTIONS = ['-n', '--app-name', '--config-var', '--header']
    OTHER_OPTIONS = ['--display-headers']

    ## FIXME: some kind of verbosity?
    ## FIXME: allow other methods than POST and GET?

    _scheme_re = re.compile(r'^[a-z][a-z]+:', re.I)

    def command(self):
        vars = {}
        app_spec = self.args[0]
        url = self.args[1]
        url = urljoin('/.command/', url)
        if self.options.config_vars:
            for item in self.option.config_vars:
                if ':' not in item:
                    raise BadCommand(
                        "Bad option, should be name:value : --config-var=%s" % item)
                name, value = item.split(':', 1)
                vars[name] = value
        headers = {}
        if self.options.headers:
            for item in self.options.headers:
                if ':' not in item:
                    raise BadCommand(
                        "Bad option, should be name:value : --header=%s" % item)
                name, value = item.split(':', 1)
                headers[name] = value.strip()
        if not self._scheme_re.search(app_spec):
            app_spec = 'config:'+app_spec
        if self.options.app_name:
            if '#' in app_spec:
                app_spec = app_spec.split('#', 1)[0]
            app_spec = app_spec + '#' + self.options.app_name
        app = loadapp(app_spec, relative_to=os.getcwd(), global_conf=vars)
        if self.command_name.lower() == 'post':
            request_method = 'POST'
        else:
            request_method = 'GET'
        qs = []
        for item in self.args[2:]:
            if '=' in item:
                item = quote(item.split('=', 1)[0]) + '=' + quote(item.split('=', 1)[1])
            else:
                item = quote(item)
            qs.append(item)
        qs = '&'.join(qs)

        environ = {
            'REQUEST_METHOD': request_method,
            ## FIXME: shouldn't be static (an option?):
            'CONTENT_TYPE': 'text/plain',
            'wsgi.run_once': True,
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.errors': sys.stderr,
            'QUERY_STRING': qs,
            'HTTP_ACCEPT': 'text/plain;q=1.0, */*;q=0.1',
            'paste.command_request': True,
            }
        if request_method == 'POST':
            environ['wsgi.input'] = sys.stdin
            environ['CONTENT_LENGTH'] = '-1'
        for name, value in headers.items():
            if name.lower() == 'content-type':
                name = 'CONTENT_TYPE'
            else:
                name = 'HTTP_'+name.upper().replace('-', '_')
            environ[name] = value

        status, headers, output, errors = raw_interactive(app, url, **environ)
        assert not errors, "errors should be printed directly to sys.stderr"
        if self.options.display_headers:
            for name, value in headers:
                sys.stdout.write('%s: %s\n' % (name, value))
            sys.stdout.write('\n')
        if six.PY3:
            sys.stdout.flush()
            sys.stdout.buffer.write(output)
            sys.stdout.buffer.flush()
        else:
            sys.stdout.write(output)
        sys.stdout.flush()
        status_int = int(status.split()[0])
        if status_int != 200:
            return status_int

    def parse_args(self, args):
        if args == ['-h']:
            Command.parse_args(self, args)
            return
        # These are the arguments parsed normally:
        normal_args = []
        # And these are arguments passed to the URL:
        extra_args = []
        # This keeps track of whether we have the two required positional arguments:
        pos_args = 0
        while args:
            start = args[0]
            if not start.startswith('-'):
                if pos_args < 2:
                    pos_args += 1
                    normal_args.append(start)
                    args.pop(0)
                    continue
                else:
                    normal_args.append(start)
                    args.pop(0)
                    continue
            else:
                found = False
                for option in self.ARG_OPTIONS:
                    if start == option:
                        normal_args.append(start)
                        args.pop(0)
                        if not args:
                            raise BadCommand(
                                "Option %s takes an argument" % option)
                        normal_args.append(args.pop(0))
                        found = True
                        break
                    elif start.startswith(option+'='):
                        normal_args.append(start)
                        args.pop(0)
                        found = True
                        break
                if found:
                    continue
                if start in self.OTHER_OPTIONS:
                    normal_args.append(start)
                    args.pop(0)
                    continue
                extra_args.append(start)
                args.pop(0)
        Command.parse_args(self, normal_args)
        # Add the extra arguments back in:
        self.args = self.args + extra_args

