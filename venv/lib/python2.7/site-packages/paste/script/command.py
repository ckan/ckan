# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
import pkg_resources
import sys
import optparse
from . import bool_optparse
import os
import re
import textwrap
from . import pluginlib
from six.moves import configparser
import getpass
from six.moves import input
try:
    import subprocess
except ImportError:
    subprocess = None # jython

difflib = None

if sys.version_info >= (2, 6):
    from logging.config import fileConfig
else:
    # Use our custom fileConfig -- 2.5.1's with a custom Formatter class
    # and less strict whitespace (which were incorporated into 2.6's)
    from paste.script.util.logging_config import fileConfig

class BadCommand(Exception):

    def __init__(self, message, exit_code=2):
        self.message = message
        self.exit_code = exit_code
        Exception.__init__(self, message)

    def _get_message(self):
        """Getter for 'message'; needed only to override deprecation
        in BaseException."""
        return self.__message

    def _set_message(self, value):
        """Setter for 'message'; needed only to override deprecation
        in BaseException."""
        self.__message = value

    # BaseException.message has been deprecated since Python 2.6.
    # To prevent DeprecationWarning from popping up over this
    # pre-existing attribute, use a new property that takes lookup
    # precedence.
    message = property(_get_message, _set_message)

class NoDefault(object):
    pass

dist = pkg_resources.get_distribution('PasteScript')

python_version = sys.version.splitlines()[0].strip()

parser = optparse.OptionParser(add_help_option=False,
                               version='%s from %s (python %s)'
                               % (dist, dist.location, python_version),
                               usage='%prog [paster_options] COMMAND [command_options]')

parser.add_option(
    '--plugin',
    action='append',
    dest='plugins',
    help="Add a plugin to the list of commands (plugins are Egg specs; will also require() the Egg)")
parser.add_option(
    '-h', '--help',
    action='store_true',
    dest='do_help',
    help="Show this help message")
parser.disable_interspersed_args()

# @@: Add an option to run this in another Python interpreter

system_plugins = []

def run(args=None):
    if (not args and
        len(sys.argv) >= 2
        and os.environ.get('_') and sys.argv[0] != os.environ['_']
        and os.environ['_'] == sys.argv[1]):
        # probably it's an exe execution
        args = ['exe', os.environ['_']] + sys.argv[2:]
    if args is None:
        args = sys.argv[1:]
    options, args = parser.parse_args(args)
    options.base_parser = parser
    system_plugins.extend(options.plugins or [])
    commands = get_commands()
    if options.do_help:
        args = ['help'] + args
    if not args:
        print('Usage: %s COMMAND' % sys.argv[0])
        args = ['help']
    command_name = args[0]
    if command_name not in commands:
        command = NotFoundCommand
    else:
        command = commands[command_name].load()
    invoke(command, command_name, options, args[1:])

def parse_exe_file(config):
    import shlex
    p = configparser.RawConfigParser()
    p.read([config])
    command_name = 'exe'
    options = []
    if p.has_option('exe', 'command'):
        command_name = p.get('exe', 'command')
    if p.has_option('exe', 'options'):
        options = shlex.split(p.get('exe', 'options'))
    if p.has_option('exe', 'sys.path'):
        paths = shlex.split(p.get('exe', 'sys.path'))
        paths = [os.path.abspath(os.path.join(os.path.dirname(config), p))
                 for p in paths]
        for path in paths:
            pkg_resources.working_set.add_entry(path)
            sys.path.insert(0, path)
    args = [command_name, config] + options
    return args

def get_commands():
    plugins = system_plugins[:]
    egg_info_dir = pluginlib.find_egg_info_dir(os.getcwd())
    if egg_info_dir:
        plugins.append(os.path.splitext(os.path.basename(egg_info_dir))[0])
        base_dir = os.path.dirname(egg_info_dir)
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)
            pkg_resources.working_set.add_entry(base_dir)
    plugins = pluginlib.resolve_plugins(plugins)
    commands = pluginlib.load_commands_from_plugins(plugins)
    commands.update(pluginlib.load_global_commands())
    return commands

def invoke(command, command_name, options, args):
    try:
        runner = command(command_name)
        exit_code = runner.run(args)
    except BadCommand as e:
        print(e.message)
        exit_code = e.exit_code
    sys.exit(exit_code)


class Command(object):

    def __init__(self, name):
        self.command_name = name

    max_args = None
    max_args_error = 'You must provide no more than %(max_args)s arguments'
    min_args = None
    min_args_error = 'You must provide at least %(min_args)s arguments'
    required_args = None
    # If this command takes a configuration file, set this to 1 or -1
    # Then if invoked through #! the config file will be put into the positional
    # arguments -- at the beginning with 1, at the end with -1
    takes_config_file = None

    # Grouped in help messages by this:
    group_name = ''

    required_args = ()
    description = None
    usage = ''
    hidden = False
    # This is the default verbosity level; --quiet subtracts,
    # --verbose adds:
    default_verbosity = 0
    # This is the default interactive state:
    default_interactive = 0
    return_code = 0

    BadCommand = BadCommand

    # Must define:
    #   parser
    #   summary
    #   command()

    def run(self, args):
        self.parse_args(args)

        # Setup defaults:
        for name, default in [('verbose', 0),
                              ('quiet', 0),
                              ('interactive', False),
                              ('overwrite', False)]:
            if not hasattr(self.options, name):
                setattr(self.options, name, default)
        if getattr(self.options, 'simulate', False):
            self.options.verbose = max(self.options.verbose, 1)
        self.interactive = self.default_interactive
        if getattr(self.options, 'interactive', False):
            self.interactive += self.options.interactive
        if getattr(self.options, 'no_interactive', False):
            self.interactive = False
        self.verbose = self.default_verbosity
        self.verbose += self.options.verbose
        self.verbose -= self.options.quiet
        self.simulate = getattr(self.options, 'simulate', False)

        # For #! situations:
        if (os.environ.get('PASTE_CONFIG_FILE')
            and self.takes_config_file is not None):
            take = self.takes_config_file
            filename = os.environ.get('PASTE_CONFIG_FILE')
            if take == 1:
                self.args.insert(0, filename)
            elif take == -1:
                self.args.append(filename)
            else:
                assert 0, (
                    "Value takes_config_file must be None, 1, or -1 (not %r)"
                    % take)

        if (os.environ.get('PASTE_DEFAULT_QUIET')):
            self.verbose = 0

        # Validate:
        if self.min_args is not None and len(self.args) < self.min_args:
            raise BadCommand(
                self.min_args_error % {'min_args': self.min_args,
                                       'actual_args': len(self.args)})
        if self.max_args is not None and len(self.args) > self.max_args:
            raise BadCommand(
                self.max_args_error % {'max_args': self.max_args,
                                       'actual_args': len(self.args)})
        for var_name, option_name in self.required_args:
            if not getattr(self.options, var_name, None):
                raise BadCommand(
                    'You must provide the option %s' % option_name)
        result = self.command()
        if result is None:
            return self.return_code
        else:
            return result

    def parse_args(self, args):
        if self.usage:
            usage = ' '+self.usage
        else:
            usage = ''
        self.parser.usage = "%%prog [options]%s\n%s" % (
            usage, self.summary)
        self.parser.prog = self._prog_name()
        if self.description:
            desc = self.description
            desc = textwrap.dedent(desc)
            self.parser.description = desc
        self.options, self.args = self.parser.parse_args(args)

    def _prog_name(self):
        return '%s %s' % (os.path.basename(sys.argv[0]), self.command_name)

    ########################################
    ## Utility methods
    ########################################

    def here(cls):
        mod = sys.modules[cls.__module__]
        return os.path.dirname(mod.__file__)

    here = classmethod(here)

    def ask(self, prompt, safe=False, default=True):
        """
        Prompt the user.  Default can be true, false, ``'careful'`` or
        ``'none'``.  If ``'none'`` then the user must enter y/n.  If
        ``'careful'`` then the user must enter yes/no (long form).

        If the interactive option is over two (``-ii``) then ``safe``
        will be used as a default.  This option should be the
        do-nothing option.
        """
        # @@: Should careful be a separate argument?

        if self.options.interactive >= 2:
            default = safe
        if default == 'careful':
            prompt += ' [yes/no]?'
        elif default == 'none':
            prompt += ' [y/n]?'
        elif default:
            prompt += ' [Y/n]? '
        else:
            prompt += ' [y/N]? '
        while 1:
            response = input(prompt).strip().lower()
            if not response:
                if default in ('careful', 'none'):
                    print('Please enter yes or no')
                    continue
                return default
            if default == 'careful':
                if response in ('yes', 'no'):
                    return response == 'yes'
                print('Please enter "yes" or "no"')
                continue
            if response[0].lower() in ('y', 'n'):
                return response[0].lower() == 'y'
            print('Y or N please')

    def challenge(self, prompt, default=NoDefault, should_echo=True):
        """
        Prompt the user for a variable.
        """
        if default is not NoDefault:
            prompt += ' [%r]' % default
        prompt += ': '
        while 1:
            if should_echo:
                prompt_method = input
            else:
                prompt_method = getpass.getpass
            response = prompt_method(prompt).strip()
            if not response:
                if default is not NoDefault:
                    return default
                else:
                    continue
            else:
                return response

    def pad(self, s, length, dir='left'):
        if len(s) >= length:
            return s
        if dir == 'left':
            return s + ' '*(length-len(s))
        else:
            return ' '*(length-len(s)) + s

    def standard_parser(cls, verbose=True,
                        interactive=False,
                        no_interactive=False,
                        simulate=False,
                        quiet=False,
                        overwrite=False):
        """
        Create a standard ``OptionParser`` instance.

        Typically used like::

            class MyCommand(Command):
                parser = Command.standard_parser()

        Subclasses may redefine ``standard_parser``, so use the
        nearest superclass's class method.
        """
        parser = bool_optparse.BoolOptionParser()
        if verbose:
            parser.add_option('-v', '--verbose',
                              action='count',
                              dest='verbose',
                              default=0)
        if quiet:
            parser.add_option('-q', '--quiet',
                              action='count',
                              dest='quiet',
                              default=0)
        if no_interactive:
            parser.add_option('--no-interactive',
                              action="count",
                              dest="no_interactive",
                              default=0)
        if interactive:
            parser.add_option('-i', '--interactive',
                              action='count',
                              dest='interactive',
                              default=0)
        if simulate:
            parser.add_option('-n', '--simulate',
                              action='store_true',
                              dest='simulate',
                              default=False)
        if overwrite:
            parser.add_option('-f', '--overwrite',
                              dest="overwrite",
                              action="store_true",
                              help="Overwrite files (warnings will be emitted for non-matching files otherwise)")
        return parser

    standard_parser = classmethod(standard_parser)

    def shorten(self, fn, *paths):
        """
        Return a shorted form of the filename (relative to the current
        directory), typically for displaying in messages.  If
        ``*paths`` are present, then use os.path.join to create the
        full filename before shortening.
        """
        if paths:
            fn = os.path.join(fn, *paths)
        if fn.startswith(os.getcwd()):
            return fn[len(os.getcwd()):].lstrip(os.path.sep)
        else:
            return fn

    def ensure_dir(self, dir, svn_add=True):
        """
        Ensure that the directory exists, creating it if necessary.
        Respects verbosity and simulation.

        Adds directory to subversion if ``.svn/`` directory exists in
        parent, and directory was created.
        """
        dir = dir.rstrip(os.sep)
        if not dir:
            # we either reached the parent-most directory, or we got
            # a relative directory
            # @@: Should we make sure we resolve relative directories
            # first?  Though presumably the current directory always
            # exists.
            return
        if not os.path.exists(dir):
            self.ensure_dir(os.path.dirname(dir))
            if self.verbose:
                print('Creating %s' % self.shorten(dir))
            if not self.simulate:
                os.mkdir(dir)
            if (svn_add and
                os.path.exists(os.path.join(os.path.dirname(dir), '.svn'))):
                self.svn_command('add', dir)
        else:
            if self.verbose > 1:
                print("Directory already exists: %s" % self.shorten(dir))

    def ensure_file(self, filename, content, svn_add=True):
        """
        Ensure a file named ``filename`` exists with the given
        content.  If ``--interactive`` has been enabled, this will ask
        the user what to do if a file exists with different content.
        """
        global difflib
        assert content is not None, (
            "You cannot pass a content of None")
        self.ensure_dir(os.path.dirname(filename), svn_add=svn_add)
        if not os.path.exists(filename):
            if self.verbose:
                print('Creating %s' % filename)
            if not self.simulate:
                f = open(filename, 'wb')
                f.write(content)
                f.close()
            if svn_add and os.path.exists(os.path.join(os.path.dirname(filename), '.svn')):
                self.svn_command('add', filename,
                                 warn_returncode=True)
            return
        f = open(filename, 'rb')
        old_content = f.read()
        f.close()
        if content == old_content:
            if self.verbose > 1:
                print('File %s matches expected content' % filename)
            return
        if not self.options.overwrite:
            print('Warning: file %s does not match expected content' % filename)
            if difflib is None:
                import difflib
            diff = difflib.context_diff(
                content.splitlines(),
                old_content.splitlines(),
                'expected ' + filename,
                filename)
            print('\n'.join(diff))
            if self.interactive:
                while 1:
                    s = input(
                        'Overwrite file with new content? [y/N] ').strip().lower()
                    if not s:
                        s = 'n'
                    if s.startswith('y'):
                        break
                    if s.startswith('n'):
                        return
                    print('Unknown response; Y or N please')
            else:
                return

        if self.verbose:
            print('Overwriting %s with new content' % filename)
        if not self.simulate:
            f = open(filename, 'wb')
            f.write(content)
            f.close()

    def insert_into_file(self, filename, marker_name, text,
                         indent=False):
        """
        Inserts ``text`` into the file, right after the given marker.
        Markers look like: ``-*- <marker_name>[:]? -*-``, and the text
        will go on the immediately following line.

        Raises ``ValueError`` if the marker is not found.

        If ``indent`` is true, then the text will be indented at the
        same level as the marker.
        """
        if not text.endswith('\n'):
            raise ValueError(
                "The text must end with a newline: %r" % text)
        if not os.path.exists(filename) and self.simulate:
            # If we are doing a simulation, it's expected that some
            # files won't exist...
            if self.verbose:
                print('Would (if not simulating) insert text into %s' % (
                    self.shorten(filename)))
            return

        f = open(filename)
        lines = f.readlines()
        f.close()
        regex = re.compile(r'-\*-\s+%s:?\s+-\*-' % re.escape(marker_name),
                           re.I)
        for i in range(len(lines)):
            if regex.search(lines[i]):
                # Found it!
                if (lines[i:] and len(lines[i:]) > 1 and
                    ''.join(lines[i+1:]).strip().startswith(text.strip())):
                    # Already have it!
                    print('Warning: line already found in %s (not inserting' % filename)
                    print('  %s' % lines[i])
                    return

                if indent:
                    text = text.lstrip()
                    match = re.search(r'^[ \t]*', lines[i])
                    text = match.group(0) + text
                lines[i+1:i+1] = [text]
                break
        else:
            errstr = (
                "Marker '-*- %s -*-' not found in %s"
                % (marker_name, filename))
            if 1 or self.simulate: # @@: being permissive right now
                print('Warning: %s' % errstr)
            else:
                raise ValueError(errstr)
        if self.verbose:
            print('Updating %s' % self.shorten(filename))
        if not self.simulate:
            f = open(filename, 'w')
            f.write(''.join(lines))
            f.close()

    def run_command(self, cmd, *args, **kw):
        """
        Runs the command, respecting verbosity and simulation.
        Returns stdout, or None if simulating.

        Keyword arguments:

        cwd:
            the current working directory to run the command in
        capture_stderr:
            if true, then both stdout and stderr will be returned
        expect_returncode:
            if true, then don't fail if the return code is not 0
        force_no_simulate:
            if true, run the command even if --simulate
        """
        if subprocess is None:
            raise RuntimeError('Environment does not support subprocess '
                               'module, cannot run command.')
        cmd = self.quote_first_command_arg(cmd)
        cwd = popdefault(kw, 'cwd', os.getcwd())
        capture_stderr = popdefault(kw, 'capture_stderr', False)
        expect_returncode = popdefault(kw, 'expect_returncode', False)
        force = popdefault(kw, 'force_no_simulate', False)
        warn_returncode = popdefault(kw, 'warn_returncode', False)
        if warn_returncode:
            expect_returncode = True
        simulate = self.simulate
        if force:
            simulate = False
        assert not kw, ("Arguments not expected: %s" % kw)
        if capture_stderr:
            stderr_pipe = subprocess.STDOUT
        else:
            stderr_pipe = subprocess.PIPE
        try:
            proc = subprocess.Popen([cmd] + list(args),
                                    cwd=cwd,
                                    stderr=stderr_pipe,
                                    stdout=subprocess.PIPE)
        except OSError as e:
            if e.errno != 2:
                # File not found
                raise
            raise OSError(
                "The expected executable %s was not found (%s)"
                % (cmd, e))
        if self.verbose:
            print('Running %s %s' % (cmd, ' '.join(args)))
        if simulate:
            return None
        stdout, stderr = proc.communicate()
        if proc.returncode and not expect_returncode:
            if not self.verbose:
                print('Running %s %s' % (cmd, ' '.join(args)))
            print('Error (exit code: %s)' % proc.returncode)
            if stderr:
                print(stderr)
            raise OSError("Error executing command %s" % cmd)
        if self.verbose > 2:
            if stderr:
                print('Command error output:')
                print(stderr)
            if stdout:
                print('Command output:')
                print(stdout)
        elif proc.returncode and warn_returncode:
            print('Warning: command failed (%s %s)' % (cmd, ' '.join(args)))
            print('Exited with code %s' % proc.returncode)
        return stdout

    def quote_first_command_arg(self, arg):
        """
        There's a bug in Windows when running an executable that's
        located inside a path with a space in it.  This method handles
        that case, or on non-Windows systems or an executable with no
        spaces, it just leaves well enough alone.
        """
        if (sys.platform != 'win32'
            or ' ' not in arg):
            # Problem does not apply:
            return arg
        try:
            import win32api
        except ImportError:
            raise ValueError(
                "The executable %r contains a space, and in order to "
                "handle this issue you must have the win32api module "
                "installed" % arg)
        arg = win32api.GetShortPathName(arg)
        return arg

    _svn_failed = False

    def svn_command(self, *args, **kw):
        """
        Run an svn command, but don't raise an exception if it fails.
        """
        try:
            return self.run_command('svn', *args, **kw)
        except OSError as e:
            if not self._svn_failed:
                print('Unable to run svn command (%s); proceeding anyway' % e)
                self._svn_failed = True

    def write_file(self, filename, content, source=None,
                   binary=True, svn_add=True):
        """
        Like ``ensure_file``, but without the interactivity.  Mostly
        deprecated.  (I think I forgot it existed)
        """
        import warnings
        warnings.warn(
            "command.write_file has been replaced with "
            "command.ensure_file",
            DeprecationWarning, 2)
        if os.path.exists(filename):
            if binary:
                f = open(filename, 'rb')
            else:
                f = open(filename, 'r')
            old_content = f.read()
            f.close()
            if content == old_content:
                if self.verbose:
                    print('File %s exists with same content' % (
                        self.shorten(filename)))
                return
            if (not self.simulate and self.options.interactive):
                if not self.ask('Overwrite file %s?' % filename):
                    return
        if self.verbose > 1 and source:
            print('Writing %s from %s' % (self.shorten(filename),
                                          self.shorten(source)))
        elif self.verbose:
            print('Writing %s' % self.shorten(filename))
        if not self.simulate:
            already_existed = os.path.exists(filename)
            if binary:
                f = open(filename, 'wb')
            else:
                f = open(filename, 'w')
            f.write(content)
            f.close()
            if (not already_existed
                and svn_add
                and os.path.exists(os.path.join(os.path.dirname(filename), '.svn'))):
                self.svn_command('add', filename)

    def parse_vars(self, args):
        """
        Given variables like ``['a=b', 'c=d']`` turns it into ``{'a':
        'b', 'c': 'd'}``
        """
        result = {}
        for arg in args:
            if '=' not in arg:
                raise BadCommand(
                    'Variable assignment %r invalid (no "=")'
                    % arg)
            name, value = arg.split('=', 1)
            result[name] = value
        return result

    def read_vars(self, config, section='pastescript'):
        """
        Given a configuration filename, this will return a map of values.
        """
        result = {}
        p = configparser.RawConfigParser()
        p.read([config])
        if p.has_section(section):
            for key, value in p.items(section):
                if key.endswith('__eval__'):
                    result[key[:-len('__eval__')]] = eval(value)
                else:
                    result[key] = value
        return result

    def write_vars(self, config, vars, section='pastescript'):
        """
        Given a configuration filename, this will add items in the
        vars mapping to the configuration file.  Will create the
        configuration file if it doesn't exist.
        """
        modified = False

        p = configparser.RawConfigParser()
        if not os.path.exists(config):
            f = open(config, 'w')
            f.write('')
            f.close()
            modified = True
        p.read([config])
        if not p.has_section(section):
            p.add_section(section)
            modified = True

        existing_options = p.options(section)
        for key, value in vars.items():
            if (key not in existing_options and
                '%s__eval__' % key not in existing_options):
                if not isinstance(value, str):
                    p.set(section, '%s__eval__' % key, repr(value))
                else:
                    p.set(section, key, value)
                modified = True

        if modified:
            p.write(open(config, 'w'))

    def indent_block(self, text, indent=2, initial=None):
        """
        Indent the block of text (each line is indented).  If you give
        ``initial``, then that is used in lieue of ``indent`` for the
        first line.
        """
        if initial is None:
            initial = indent
        lines = text.splitlines()
        first = (' '*initial) + lines[0]
        rest = [(' '*indent)+l for l in lines[1:]]
        return '\n'.join([first]+rest)

    def logging_file_config(self, config_file):
        """
        Setup logging via the logging module's fileConfig function with the
        specified ``config_file``, if applicable.

        ConfigParser defaults are specified for the special ``__file__``
        and ``here`` variables, similar to PasteDeploy config loading.
        """
        parser = configparser.ConfigParser()
        parser.read([config_file])
        if parser.has_section('loggers'):
            config_file = os.path.abspath(config_file)
            fileConfig(config_file, dict(__file__=config_file,
                                         here=os.path.dirname(config_file)))

class NotFoundCommand(Command):

    def run(self, args):
        #for name, value in os.environ.items():
        #    print '%s: %s' % (name, value)
        #print sys.argv
        print(('Command %r not known (you may need to run setup.py egg_info)'
               % self.command_name))
        commands = sorted(get_commands().items())
        if not commands:
            print('No commands registered.')
            print('Have you installed Paste Script?')
            print('(try running python setup.py develop)')
            return 2
        print('Known commands:')
        longest = max([len(n) for n, c in commands])
        for name, command in commands:
            print('  %s  %s' % (self.pad(name, length=longest),
                                command.load().summary))
        return 2

def popdefault(dict, name, default=None):
    if name not in dict:
        return default
    else:
        v = dict[name]
        del dict[name]
        return v
