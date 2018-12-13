# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Provides the two commands for preparing an application:
``prepare-app`` and ``setup-app``
"""
from __future__ import print_function

import types
import os
import six
import string
import uuid
from paste.deploy import appconfig
from paste.script import copydir
from paste.script.command import Command, BadCommand, run as run_command
from paste.script.util import secret
from paste.util import import_string
from six.moves import filter
import paste.script.templates
import pkg_resources

Cheetah = None

class AbstractInstallCommand(Command):

    default_interactive = 1

    default_sysconfigs = [
        (False, '/etc/paste/sysconfig.py'),
        (False, '/usr/local/etc/paste/sysconfig.py'),
        (True, 'paste.script.default_sysconfig'),
        ]
    if os.environ.get('HOME'):
        default_sysconfigs.insert(
            0, (False, os.path.join(os.environ['HOME'], '.paste', 'config',
                                    'sysconfig.py')))
    if os.environ.get('PASTE_SYSCONFIG'):
        default_sysconfigs.insert(
            0, (False, os.environ['PASTE_SYSCONFIG']))

    def run(self, args):
        # This is overridden so we can parse sys-config before we pass
        # it to optparse
        self.sysconfigs = self.default_sysconfigs
        new_args = []
        while args:
            if args[0].startswith('--no-default-sysconfig'):
                self.sysconfigs = []
                args.pop(0)
                continue
            if args[0].startswith('--sysconfig='):
                self.sysconfigs.insert(
                    0, (True, args.pop(0)[len('--sysconfig='):]))
                continue
            if args[0] == '--sysconfig':
                args.pop(0)
                if not args:
                    raise BadCommand(
                        "You gave --sysconfig as the last argument without "
                        "a value")
                self.sysconfigs.insert(0, (True, args.pop(0)))
                continue
            new_args.append(args.pop(0))
        self.load_sysconfigs()
        return super(AbstractInstallCommand, self).run(new_args)

    #@classmethod
    def standard_parser(cls, **kw):
        parser = super(AbstractInstallCommand, cls).standard_parser(**kw)
        parser.add_option('--sysconfig',
                          action="append",
                          dest="sysconfigs",
                          help="System configuration file")
        parser.add_option('--no-default-sysconfig',
                          action='store_true',
                          dest='no_default_sysconfig',
                          help="Don't load the default sysconfig files")
        parser.add_option(
            '--easy-install',
            action='append',
            dest='easy_install_op',
            metavar='OP',
            help='An option to add if invoking easy_install (like --easy-install=exclude-scripts)')
        parser.add_option(
            '--no-install',
            action='store_true',
            dest='no_install',
            help="Don't try to install the package (it must already be installed)")
        parser.add_option(
            '-f', '--find-links',
            action='append',
            dest='easy_install_find_links',
            metavar='URL',
            help='Passed through to easy_install')

        return parser

    standard_parser = classmethod(standard_parser)

    ########################################
    ## Sysconfig Handling
    ########################################

    def load_sysconfigs(self):
        configs = self.sysconfigs[:]
        configs.reverse()
        self.sysconfig_modules = []
        for index, (explicit, name) in enumerate(configs):
            # @@: At some point I'd like to give the specialized
            # modules some access to the values in earlier modules,
            # e.g., to specialize those values or functions.  That's
            # why these modules are loaded backwards.
            if name.endswith('.py'):
                if not os.path.exists(name):
                    if explicit:
                        raise BadCommand(
                            "sysconfig file %s does not exist"
                            % name)
                    else:
                        continue
                globs = {}
                six.exec_(compile(open(name).read(), name, 'exec'), globs)
                mod = types.ModuleType('__sysconfig_%i__' % index)
                for name, value in globs.items():
                    setattr(mod, name, value)
                mod.__file__ = name
            else:
                try:
                    mod = import_string.simple_import(name)
                except ImportError:
                    if explicit:
                        raise
                    else:
                        continue
            mod.paste_command = self
            self.sysconfig_modules.insert(0, mod)
        # @@: I'd really prefer to clone the parser here somehow,
        # not to modify it in place
        parser = self.parser
        self.call_sysconfig_functions('add_custom_options', parser)

    def get_sysconfig_option(self, name, default=None):
        """
        Return the value of the given option in the first sysconfig
        module in which it is found, or ``default`` (None) if not
        found in any.
        """
        for mod in self.sysconfig_modules:
            if hasattr(mod, name):
                return getattr(mod, name)
        return default

    def get_sysconfig_options(self, name):
        """
        Return the option value for the given name in all the
        sysconfig modules in which is is found (``[]`` if none).
        """
        return [getattr(mod, name) for mod in self.sysconfig_modules
                if hasattr(mod, name)]

    def call_sysconfig_function(self, name, *args, **kw):
        """
        Call the specified function in the first sysconfig module it
        is defined in.  ``NameError`` if no function is found.
        """
        val = self.get_sysconfig_option(name)
        if val is None:
            raise NameError(
                "Method %s not found in any sysconfig module" % name)
        return val(*args, **kw)

    def call_sysconfig_functions(self, name, *args, **kw):
        """
        Call all the named functions in the sysconfig modules,
        returning a list of the return values.
        """
        return [method(*args, **kw) for method in
                self.get_sysconfig_options(name)]

    def sysconfig_install_vars(self, installer):
        """
        Return the folded results of calling the
        ``install_variables()`` functions.
        """
        result = {}
        all_vars = self.call_sysconfig_functions(
            'install_variables', installer)
        all_vars.reverse()
        for vardict in all_vars:
            result.update(vardict)
        return result

    ########################################
    ## Distributions
    ########################################

    def get_distribution(self, req):
        """
        This gets a distribution object, and installs the distribution
        if required.
        """
        try:
            dist = pkg_resources.get_distribution(req)
            if self.verbose:
                print('Distribution already installed:')
                print(' ', dist, 'from', dist.location)
            return dist
        except pkg_resources.DistributionNotFound:
            if self.options.no_install:
                print("Because --no-install was given, we won't try to install the package %s" % req)
                raise
            options = ['-v', '-m']
            for op in self.options.easy_install_op or []:
                if not op.startswith('-'):
                    op = '--'+op
                options.append(op)
            for op in self.options.easy_install_find_links or []:
                options.append('--find-links=%s' % op)
            if self.simulate:
                raise BadCommand(
                    "Must install %s, but in simulation mode" % req)
            print("Must install %s" % req)
            from setuptools.command import easy_install
            from setuptools import setup
            setup(script_args=['-q', 'easy_install']
                  + options + [req])
            return pkg_resources.get_distribution(req)

    def get_installer(self, distro, ep_group, ep_name):
        installer_class = distro.load_entry_point(
            'paste.app_install', ep_name)
        installer = installer_class(
            distro, ep_group, ep_name)
        return installer


class MakeConfigCommand(AbstractInstallCommand):

    default_verbosity = 1
    max_args = None
    min_args = 1
    summary = "Install a package and create a fresh config file/directory"
    usage = "PACKAGE_NAME [CONFIG_FILE] [VAR=VALUE]"

    description = """\
    Note: this is an experimental command, and it will probably change
    in several ways by the next release.

    make-config is part of a two-phase installation process (the
    second phase is setup-app).  make-config installs the package
    (using easy_install) and asks it to create a bare configuration
    file or directory (possibly filling in defaults from the extra
    variables you give).
    """

    parser = AbstractInstallCommand.standard_parser(
        simulate=True, quiet=True, no_interactive=True)
    parser.add_option('--info',
                      action="store_true",
                      dest="show_info",
                      help="Show information on the package (after installing it), but do not write a config.")
    parser.add_option('--name',
                      action='store',
                      dest='ep_name',
                      help='The name of the application contained in the distribution (default "main")')
    parser.add_option('--entry-group',
                      action='store',
                      dest='ep_group',
                      default='paste.app_factory',
                      help='The entry point group to install (i.e., the kind of application; default paste.app_factory')
    parser.add_option('--edit',
                      action='store_true',
                      dest='edit',
                      help='Edit the configuration file after generating it (using $EDITOR)')
    parser.add_option('--setup',
                      action='store_true',
                      dest='run_setup',
                      help='Run setup-app immediately after generating (and possibly editing) the configuration file')

    def command(self):
        self.requirement = self.args[0]
        if '#' in self.requirement:
            if self.options.ep_name is not None:
                raise BadCommand(
                    "You may not give both --name and a requirement with "
                    "#name")
            self.requirement, self.options.ep_name = self.requirement.split('#', 1)
        if not self.options.ep_name:
            self.options.ep_name = 'main'
        self.distro = self.get_distribution(self.requirement)
        self.installer = self.get_installer(
            self.distro, self.options.ep_group, self.options.ep_name)
        if self.options.show_info:
            if len(self.args) > 1:
                raise BadCommand(
                    "With --info you can only give one argument")
            return self.show_info()
        if len(self.args) < 2:
            # See if sysconfig can give us a default filename
            options = filter(None, self.call_sysconfig_functions(
                'default_config_filename', self.installer))
            if not options:
                raise BadCommand(
                    "You must give a configuration filename")
            self.config_file = options[0]
        else:
            self.config_file = self.args[1]
        self.check_config_file()
        self.project_name = self.distro.project_name
        self.vars = self.sysconfig_install_vars(self.installer)
        self.vars.update(self.parse_vars(self.args[2:]))
        self.vars['project_name'] = self.project_name
        self.vars['requirement'] = self.requirement
        self.vars['ep_name'] = self.options.ep_name
        self.vars['ep_group'] = self.options.ep_group
        self.vars.setdefault('app_name', self.project_name.lower())
        self.vars.setdefault('app_instance_uuid', uuid.uuid4())
        self.vars.setdefault('app_instance_secret', secret.secret_string())
        if self.verbose > 1:
            print_vars = sorted(self.vars.items())
            print('Variables for installation:')
            for name, value in print_vars:
                print('  %s: %r' % (name, value))
        self.installer.write_config(self, self.config_file, self.vars)
        edit_success = True
        if self.options.edit:
            edit_success = self.run_editor()
        setup_configs = self.installer.editable_config_files(self.config_file)
        # @@: We'll just assume the first file in the list is the one
        # that works with setup-app...
        setup_config = setup_configs[0]
        if self.options.run_setup:
            if not edit_success:
                print('Config-file editing was not successful.')
                if self.ask('Run setup-app anyway?', default=False):
                    self.run_setup(setup_config)
            else:
                self.run_setup(setup_config)
        else:
            filenames = self.installer.editable_config_files(self.config_file)
            assert not isinstance(filenames, six.string_types), (
                "editable_config_files returned a string, not a list")
            if not filenames and filenames is not None:
                print('No config files need editing')
            else:
                print('Now you should edit the config files')
                if filenames:
                    for fn in filenames:
                        print('  %s' % fn)

    def show_info(self):
        text = self.installer.description(None)
        print(text)

    def check_config_file(self):
        if self.installer.expect_config_directory is None:
            return
        fn = self.config_file
        if self.installer.expect_config_directory:
            if os.path.splitext(fn)[1]:
                raise BadCommand(
                    "The CONFIG_FILE argument %r looks like a filename, "
                    "and a directory name is expected" % fn)
        else:
            if fn.endswith('/') or not os.path.splitext(fn):
                raise BadCommand(
                    "The CONFIG_FILE argument %r looks like a directory "
                    "name and a filename is expected" % fn)

    def run_setup(self, filename):
        run_command(['setup-app', filename])

    def run_editor(self):
        filenames = self.installer.editable_config_files(self.config_file)
        if filenames is None:
            print('Warning: the config file is not known (--edit ignored)')
            return False
        if not filenames:
            print('Warning: no config files need editing (--edit ignored)')
            return True
        if len(filenames) > 1:
            print('Warning: there is more than one editable config file (--edit ignored)')
            return False
        if not os.environ.get('EDITOR'):
            print('Error: you must set $EDITOR if using --edit')
            return False
        if self.verbose:
            print('%s %s' % (os.environ['EDITOR'], filenames[0]))
        retval = os.system('$EDITOR %s' % filenames[0])
        if retval:
            print('Warning: editor %s returned with error code %i' % (
                os.environ['EDITOR'], retval))
            return False
        return True

class SetupCommand(AbstractInstallCommand):

    default_verbosity = 1
    max_args = 1
    min_args = 1
    summary = "Setup an application, given a config file"
    usage = "CONFIG_FILE"

    description = """\
    Note: this is an experimental command, and it will probably change
    in several ways by the next release.

    Setup an application according to its configuration file.  This is
    the second part of a two-phase web application installation
    process (the first phase is prepare-app).  The setup process may
    consist of things like creating directories and setting up
    databases.
    """

    parser = AbstractInstallCommand.standard_parser(
        simulate=True, quiet=True, interactive=True)
    parser.add_option('--name',
                      action='store',
                      dest='section_name',
                      default=None,
                      help='The name of the section to set up (default: app:main)')

    def command(self):
        config_spec = self.args[0]
        section = self.options.section_name
        if section is None:
            if '#' in config_spec:
                config_spec, section = config_spec.split('#', 1)
            else:
                section = 'main'
        if not ':' in section:
            plain_section = section
            section = 'app:'+section
        else:
            plain_section = section.split(':', 1)[0]
        if not config_spec.startswith('config:'):
            config_spec = 'config:' + config_spec
        if plain_section != 'main':
            config_spec += '#' + plain_section
        config_file = config_spec[len('config:'):].split('#', 1)[0]
        config_file = os.path.join(os.getcwd(), config_file)
        self.logging_file_config(config_file)
        conf = appconfig(config_spec, relative_to=os.getcwd())
        ep_name = conf.context.entry_point_name
        ep_group = conf.context.protocol
        dist = conf.context.distribution
        if dist is None:
            raise BadCommand(
                "The section %r is not the application (probably a filter).  You should add #section_name, where section_name is the section that configures your application" % plain_section)
        installer = self.get_installer(dist, ep_group, ep_name)
        installer.setup_config(
            self, config_file, section, self.sysconfig_install_vars(installer))
        self.call_sysconfig_functions(
            'post_setup_hook', installer, config_file)


class Installer(object):

    """
    Abstract base class for installers, and also a generic
    installer that will run off config files in the .egg-info
    directory of a distribution.

    Packages that simply refer to this installer can provide a file
    ``*.egg-info/paste_deploy_config.ini_tmpl`` that will be
    interpreted by Cheetah.  They can also provide ``websetup``
    modules with a ``setup_app(command, conf, vars)`` (or the
    now-deprecated ``setup_config(command, filename, section, vars)``)
    function, that will be called.

    In the future other functions or configuration files may be
    called.
    """

    # If this is true, then try to detect filename-looking config_file
    # values, and reject them.  Conversely, if false try to detect
    # directory-looking values and reject them.  None means don't
    # check.
    expect_config_directory = False

    # Set this to give a default config filename when none is
    # specified:
    default_config_filename = None

    # Set this to true to use Cheetah to fill your templates, or false
    # to not do so:
    use_cheetah = True

    def __init__(self, dist, ep_group, ep_name):
        self.dist = dist
        self.ep_group = ep_group
        self.ep_name = ep_name

    def description(self, config):
        return 'An application'

    def write_config(self, command, filename, vars):
        """
        Writes the content to the filename (directory or single file).
        You should use the ``command`` object, which respects things
        like simulation and interactive.  ``vars`` is a dictionary
        of user-provided variables.
        """
        command.ensure_file(filename, self.config_content(command, vars))

    def editable_config_files(self, filename):
        """
        Return a list of filenames; this is primarily used when the
        filename is treated as a directory and several configuration
        files are created.  The default implementation returns the
        file itself.  Return None if you don't know what files should
        be edited on installation.
        """
        if not self.expect_config_directory:
            return [filename]
        else:
            return None

    def config_content(self, command, vars):
        """
        Called by ``self.write_config``, this returns the text content
        for the config file, given the provided variables.

        The default implementation reads
        ``Package.egg-info/paste_deploy_config.ini_tmpl`` and fills it
        with the variables.
        """
        global Cheetah
        meta_name = 'paste_deploy_config.ini_tmpl'
        if not self.dist.has_metadata(meta_name):
            if command.verbose:
                print('No %s found' % meta_name)
            return self.simple_config(vars)
        return self.template_renderer(
            self.dist.get_metadata(meta_name), vars, filename=meta_name)

    def template_renderer(self, content, vars, filename=None):
        """
        Subclasses may override this to provide different template
        substitution (e.g., use a different template engine).
        """
        if self.use_cheetah:
            import Cheetah.Template
            tmpl = Cheetah.Template.Template(content,
                                             searchList=[vars])
            return copydir.careful_sub(
                tmpl, vars, filename)
        else:
            tmpl = string.Template(content)
            return tmpl.substitute(vars)

    def simple_config(self, vars):
        """
        Return a very simple configuration file for this application.
        """
        if self.ep_name != 'main':
            ep_name = '#'+self.ep_name
        else:
            ep_name = ''
        return ('[app:main]\n'
                'use = egg:%s%s\n'
                % (self.dist.project_name, ep_name))

    def setup_config(self, command, filename, section, vars):
        """
        Called to setup an application, given its configuration
        file/directory.

        The default implementation calls
        ``package.websetup.setup_config(command, filename, section,
        vars)`` or ``package.websetup.setup_app(command, config,
        vars)``

        With ``setup_app`` the ``config`` object is a dictionary with
        the extra attributes ``global_conf``, ``local_conf`` and
        ``filename``
        """
        modules = [
            line.strip()
            for line in self.dist.get_metadata_lines('top_level.txt')
            if line.strip() and not line.strip().startswith('#')]
        if not modules:
            print('No modules are listed in top_level.txt')
            print('Try running python setup.py egg_info to regenerate that file')
        for mod_name in modules:
            mod_name = mod_name + '.websetup'
            mod = import_string.try_import_module(mod_name)
            if mod is None:
                continue
            if hasattr(mod, 'setup_app'):
                if command.verbose:
                    print('Running setup_app() from %s' % mod_name)
                self._call_setup_app(
                    mod.setup_app, command, filename, section, vars)
            elif hasattr(mod, 'setup_config'):
                if command.verbose:
                    print('Running setup_config() from %s' % mod_name)
                mod.setup_config(command, filename, section, vars)
            else:
                print('No setup_app() or setup_config() function in %s (%s)' % (
                    mod.__name__, mod.__file__))

    def _call_setup_app(self, func, command, filename, section, vars):
        filename = os.path.abspath(filename)
        if ':' in section:
            section = section.split(':', 1)[1]
        conf = 'config:%s#%s' % (filename, section)
        conf = appconfig(conf)
        conf.filename = filename
        func(command, conf, vars)

