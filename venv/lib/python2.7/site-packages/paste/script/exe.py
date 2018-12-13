# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
import re
import os
import sys
import shlex
import pkg_resources
from . import command

class ExeCommand(command.Command):

    parser = command.Command.standard_parser(verbose=False)
    summary = "Run #! executable files"
    description = """\
Use this at the top of files like:

  #!/usr/bin/env /path/to/paster exe subcommand <command options>

The rest of the file will be used as a config file for the given
command, if it wants a config file.

You can also include an [exe] section in the file, which looks
like:

  [exe]
  command = serve
  log_file = /path/to/log
  add = /path/to/other/config.ini

Which translates to:

  paster serve --log-file=/path/to/log /path/to/other/config.ini
"""

    hidden = True

    _exe_section_re = re.compile(r'^\s*\[\s*exe\s*\]\s*$')
    _section_re = re.compile(r'^\s*\[')

    def run(self, argv):
        if argv and argv[0] in ('-h', '--help'):
            print(self.description)
            return

        if os.environ.get('REQUEST_METHOD'):
            # We're probably in a CGI environment
            sys.stdout = sys.stderr
            os.environ['PASTE_DEFAULT_QUIET'] = 'true'
            # Maybe import cgitb or something?

        if '_' not in os.environ:
            print("Warning: this command is intended to be run with a #! like:")
            print("  #!/usr/bin/env paster exe")
            print("It only works with /usr/bin/env, and only as a #! line.")
            # Should I actually shlex.split the args?
            filename = argv[-1]
            args = argv[:-1]
            extra_args = []
        else:
            filename = os.environ['_']
            extra_args = argv[:]
            args = []
            while extra_args:
                if extra_args[0] == filename:
                    extra_args.pop(0)
                    break
                args.append(extra_args.pop(0))
        vars = {'here': os.path.dirname(filename),
                '__file__': filename}
        f = open(filename)
        lines = f.readlines()
        f.close()
        options = {}
        lineno = 1
        while lines:
            if self._exe_section_re.search(lines[0]):
                lines.pop(0)
                break
            lines.pop(0)
            lineno += 1
        options = args
        for line in lines:
            lineno += 1
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if self._section_re.search(line):
                break
            if '=' not in line:
                raise command.BadCommand('Missing = in %s at %s: %r'
                                         % (filename, lineno, line))
            name, value = line.split('=', 1)
            name = name.strip()
            value = value.strip()
            if name == 'require':
                pkg_resources.require(value)
            elif name == 'command' or name == 'add':
                options.extend(shlex.split(value))
            elif name == 'plugin':
                options[:0] = ['--plugin', value]
            else:
                value = value % vars
                options.append('--%s=%s' % (name.replace('_', '-'), value))
        os.environ['PASTE_CONFIG_FILE'] = filename
        options.extend(extra_args)
        command.run(options)
