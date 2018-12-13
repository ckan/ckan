"""Paster Commands, for use with paster in your project

.. highlight:: bash

The following commands are made available via paster utilizing
setuptools points discovery. These can be used from the command line
when the directory is the Pylons project.

Commands available:

``controller``
    Create a Controller and accompanying functional test
``restcontroller``
    Create a REST Controller and accompanying functional test
``shell``
    Open an interactive shell with the Pylons app loaded

Example usage::
    
    ~/sample$ paster controller account
    Creating /Users/ben/sample/sample/controllers/account.py
    Creating /Users/ben/sample/sample/tests/functional/test_account.py
    ~/sample$

.. admonition:: How it Works

    :command:`paster` is a command line script (from the PasteScript
    package) that allows the creation of context sensitive commands.
    :command:`paster` looks in the current directory for a 
    ``.egg-info`` directory, then loads the ``paster_plugins.txt``
    file.

    Using setuptools entry points, :command:`paster` looks for
    functions registered with setuptools as 
    :func:`paste.paster_command`. These are defined in the entry_points
    block in each packages :file:`setup.py` module.

    This same system is used when running :command:`paster create` to
    determine what templates are available when creating new projects.

"""
import os
import sys

import paste.fixture
import paste.registry
import paste.deploy.config
from paste.deploy import loadapp, appconfig
from paste.script.command import Command, BadCommand
from paste.script.filemaker import FileOp
from tempita import paste_script_template_renderer

import pylons
import pylons.util as util

__all__ = ['ControllerCommand', 'RestControllerCommand', 'ShellCommand']

def can_import(name):
    """Attempt to __import__ the specified package/module, returning
    True when succeeding, otherwise False"""
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def is_minimal_template(package, fail_fast=False):
    """Determine if the specified Pylons project (package) uses the
    Pylons Minimal Template.

    fail_fast causes ImportErrors encountered during detection to be
    raised.
    """
    minimal_template = False
    try:
        # Check if PACKAGE.lib.base exists
        __import__(package + '.lib.base')
    except ImportError, ie:
        if 'No module named lib.base' in str(ie):
            minimal_template = True
    except:
        # PACKAGE.lib.base exists but throws an error
        if fail_fast:
            raise
    return minimal_template


def defines_render(package):
    """Determine if the specified Pylons project (package) defines a
    render callable in their base module
    """
    base_module = (is_minimal_template(package) and package + '.controllers' or
                   package + '.lib.base')
    try:
        base = __import__(base_module, globals(), locals(), ['__doc__'])
    except:
        return False
    return callable(getattr(base, 'render', None))


def validate_name(name):
    """Validate that the name for the controller isn't present on the
    path already"""
    if not name:
        # This happens when the name is an existing directory
        raise BadCommand('Please give the name of a controller.')
    # 'setup' is a valid controller name, but when paster controller is ran
    # from the root directory of a project, importing setup will import the
    # project's setup.py causing a sys.exit(). Blame relative imports
    if name != 'setup' and can_import(name):
        raise BadCommand(
            "\n\nA module named '%s' is already present in your "
            "PYTHON_PATH.\nChoosing a conflicting name will likely cause "
            "import problems in\nyour controller at some point. It's "
            "suggested that you choose an\nalternate name, and if you'd "
            "like that name to be accessible as\n'%s', add a route "
            "to your projects config/routing.py file similar\nto:\n"
            "    map.connect('%s', controller='my_%s')" \
            % (name, name, name, name))
    return True


def check_controller_existance(base_package, name): 
    """Check if given controller already exists in project.""" 
    filename = os.path.join(base_package, 'controllers', name + '.py') 
    if os.path.exists(filename): 
        raise BadCommand('Controller %s already exists.' % name)


class ControllerCommand(Command):
    """Create a Controller and accompanying functional test

    The Controller command will create the standard controller template
    file and associated functional test to speed creation of
    controllers.

    Example usage::

        yourproj% paster controller comments
        Creating yourproj/yourproj/controllers/comments.py
        Creating yourproj/yourproj/tests/functional/test_comments.py

    If you'd like to have controllers underneath a directory, just
    include the path as the controller name and the necessary
    directories will be created for you::

        yourproj% paster controller admin/trackback
        Creating yourproj/controllers/admin
        Creating yourproj/yourproj/controllers/admin/trackback.py
        Creating yourproj/yourproj/tests/functional/test_admin_trackback.py

    """
    summary = __doc__.splitlines()[0]
    usage = '\n' + __doc__

    min_args = 1
    max_args = 1
    group_name = 'pylons'

    default_verbosity = 3

    parser = Command.standard_parser(simulate=True)
    parser.add_option('--no-test',
                      action='store_true',
                      dest='no_test',
                      help="Don't create the test; just the controller")

    def command(self):
        """Main command to create controller"""
        try:
            file_op = FileOp(source_dir=('pylons', 'templates'))
            try:
                name, directory = file_op.parse_path_name_args(self.args[0])
            except:
                raise BadCommand('No egg_info directory was found')

            # Check the name isn't the same as the package
            base_package = file_op.find_dir('controllers', True)[0]
            if base_package.lower() == name.lower():
                raise BadCommand(
                    'Your controller name should not be the same as '
                    'the package name %r.' % base_package)
            # Validate the name
            name = name.replace('-', '_')
            validate_name(name)

            # Determine the module's import statement
            if is_minimal_template(base_package):
                importstatement = ('from %s.controllers import BaseController'
                                   % base_package)
            else:
                importstatement = ('from %s.lib.base import BaseController' %
                                   base_package)
            if defines_render(base_package):
                importstatement += ', render'

            # Setup the controller
            fullname = os.path.join(directory, name)
            controller_name = util.class_name_from_module_name(
                name.split('/')[-1])
            if not fullname.startswith(os.sep):
                fullname = os.sep + fullname
            testname = fullname.replace(os.sep, '_')[1:]
            check_controller_existance(base_package, name)
            
            file_op.template_vars.update(
                {'name': controller_name,
                 'fname': os.path.join(directory, name),
                 'tmpl_name': name,
                 'package':base_package,
                 'importstatement': importstatement})
            file_op.copy_file(template='controller.py_tmpl',
                              dest=os.path.join('controllers', directory),
                              filename=name,
                              template_renderer=paste_script_template_renderer)
            if not self.options.no_test:
                file_op.copy_file(
                    template='test_controller.py_tmpl',
                    dest=os.path.join('tests', 'functional'),
                    filename='test_' + testname,
                    template_renderer=paste_script_template_renderer)
        except BadCommand, e:
            raise BadCommand('An error occurred. %s' % e)
        except:
            msg = str(sys.exc_info()[1])
            raise BadCommand('An unknown error occurred. %s' % msg)


class RestControllerCommand(Command):
    """Create a REST Controller and accompanying functional test

    The RestController command will create a REST-based Controller file
    for use with the :meth:`~routes.mapper.Mapper.resource`
    REST-based dispatching. This template includes the methods that
    :meth:`~routes.mapper.Mapper.resource` dispatches to in
    addition to doc strings for clarification on when the methods will
    be called.

    The first argument should be the singular form of the REST
    resource. The second argument is the plural form of the word. If
    its a nested controller, put the directory information in front as
    shown in the second example below.

    Example usage::

        yourproj% paster restcontroller comment comments
        Creating yourproj/yourproj/controllers/comments.py
        Creating yourproj/yourproj/tests/functional/test_comments.py

    If you'd like to have controllers underneath a directory, just
    include the path as the controller name and the necessary
    directories will be created for you::

        yourproj% paster restcontroller admin/tracback admin/trackbacks
        Creating yourproj/controllers/admin
        Creating yourproj/yourproj/controllers/admin/trackbacks.py
        Creating yourproj/yourproj/tests/functional/test_admin_trackbacks.py

    """
    summary = __doc__.splitlines()[0]
    usage = '\n' + __doc__

    min_args = 2
    max_args = 2
    group_name = 'pylons'

    default_verbosity = 3

    parser = Command.standard_parser(simulate=True)
    parser.add_option('--no-test',
                      action='store_true',
                      dest='no_test',
                      help="Don't create the test; just the controller")

    def command(self):
        """Main command to create controller"""
        try:
            file_op = FileOp(source_dir=('pylons', 'templates'))
            try:
                singularname, singulardirectory = \
                    file_op.parse_path_name_args(self.args[0])
                pluralname, pluraldirectory = \
                    file_op.parse_path_name_args(self.args[1])
            except:
                raise BadCommand('No egg_info directory was found')

            # Check the name isn't the same as the package
            base_package = file_op.find_dir('controllers', True)[0]
            if base_package.lower() == pluralname.lower():
                raise BadCommand(
                    'Your controller name should not be the same as '
                    'the package name %r.'% base_package)
            # Validate the name
            for name in [pluralname]:
                name = name.replace('-', '_')
                validate_name(name)

            # Determine the module's import statement
            if is_minimal_template(base_package):
                importstatement = ('from %s.controllers import BaseController'
                                   % base_package)
            else:
                importstatement = ('from %s.lib.base import BaseController' %
                                   base_package)
            if defines_render(base_package):
                importstatement += ', render'
            
            check_controller_existance(base_package, name)
            
            # Setup the controller
            fullname = os.path.join(pluraldirectory, pluralname)
            controller_name = util.class_name_from_module_name(
                pluralname.split('/')[-1])
            if not fullname.startswith(os.sep):
                fullname = os.sep + fullname
            testname = fullname.replace(os.sep, '_')[1:]

            nameprefix = ''
            if pluraldirectory:
                nameprefix = pluraldirectory.replace(os.path.sep, '_') + '_'

            controller_c = ''
            if nameprefix:
                controller_c = ", controller='%s', \n\t" % \
                    '/'.join([pluraldirectory, pluralname])
                controller_c += "path_prefix='/%s', name_prefix='%s_'" % \
                    (pluraldirectory, pluraldirectory)
            command = "map.resource('%s', '%s'%s)\n" % \
                (singularname, pluralname, controller_c)

            file_op.template_vars.update(
                {'classname': controller_name,
                 'pluralname': pluralname,
                 'singularname': singularname,
                 'name': controller_name,
                 'nameprefix': nameprefix,
                 'package':base_package,
                 'resource_command': command.replace('\n\t', '\n%s#%s' % \
                                                         (' '*4, ' '*9)),
                 'fname': os.path.join(pluraldirectory, pluralname),
                 'importstatement': importstatement})

            resource_command = ("\nTo create the appropriate RESTful mapping, "
                                "add a map statement to your\n")
            resource_command += ("config/routing.py file near the top like "
                                 "this:\n\n")
            resource_command += command
            file_op.copy_file(template='restcontroller.py_tmpl',
                              dest=os.path.join('controllers', pluraldirectory),
                              filename=pluralname,
                              template_renderer=paste_script_template_renderer)
            if not self.options.no_test:
                file_op.copy_file(
                    template='test_restcontroller.py_tmpl',
                    dest=os.path.join('tests', 'functional'),
                    filename='test_' + testname,
                    template_renderer=paste_script_template_renderer)
            print resource_command
        except BadCommand, e:
            raise BadCommand('An error occurred. %s' % e)
        except:
            msg = str(sys.exc_info()[1])
            raise BadCommand('An unknown error occurred. %s' % msg)


class ShellCommand(Command):
    """Open an interactive shell with the Pylons app loaded

    The optional CONFIG_FILE argument specifies the config file to use for
    the interactive shell. CONFIG_FILE defaults to 'development.ini'.

    This allows you to test your mapper, models, and simulate web requests
    using ``paste.fixture``.

    Example::

        $ paster shell my-development.ini

    """
    summary = __doc__.splitlines()[0]
    usage = '\n' + __doc__

    min_args = 0
    max_args = 1
    group_name = 'pylons'

    parser = Command.standard_parser(simulate=True)
    parser.add_option('-d', '--disable-ipython',
                      action='store_true',
                      dest='disable_ipython',
                      help="Don't use IPython if it is available")

    parser.add_option('-q',
                      action='count',
                      dest='quiet',
                      default=0,
                      help=("Do not load logging configuration from the "
                            "config file"))

    def command(self):
        """Main command to create a new shell"""
        self.verbose = 3
        if len(self.args) == 0:
            # Assume the .ini file is ./development.ini
            config_file = 'development.ini'
            if not os.path.isfile(config_file):
                raise BadCommand('%sError: CONFIG_FILE not found at: .%s%s\n'
                                 'Please specify a CONFIG_FILE' % \
                                 (self.parser.get_usage(), os.path.sep,
                                  config_file))
        else:
            config_file = self.args[0]

        config_name = 'config:%s' % config_file
        here_dir = os.getcwd()
        locs = dict(__name__="pylons-admin")

        if not self.options.quiet:
            # Configure logging from the config file
            self.logging_file_config(config_file)
        
        # XXX: Note, initializing CONFIG here is Legacy support. pylons.config
        # will automatically be initialized and restored via the registry
        # restorer along with the other StackedObjectProxys
        # Load app config into paste.deploy to simulate request config
        # Setup the Paste CONFIG object, adding app_conf/global_conf for legacy
        # code
        conf = appconfig(config_name, relative_to=here_dir)
        conf.update(dict(app_conf=conf.local_conf,
                         global_conf=conf.global_conf))
        paste.deploy.config.CONFIG.push_thread_config(conf)

        # Load locals and populate with objects for use in shell
        sys.path.insert(0, here_dir)

        # Load the wsgi app first so that everything is initialized right
        wsgiapp = loadapp(config_name, relative_to=here_dir)
        test_app = paste.fixture.TestApp(wsgiapp)

        # Query the test app to setup the environment
        tresponse = test_app.get('/_test_vars')
        request_id = int(tresponse.body)

        # Disable restoration during test_app requests
        test_app.pre_request_hook = lambda self: \
            paste.registry.restorer.restoration_end()
        test_app.post_request_hook = lambda self: \
            paste.registry.restorer.restoration_begin(request_id)

        # Restore the state of the Pylons special objects
        # (StackedObjectProxies)
        paste.registry.restorer.restoration_begin(request_id)
                
        # Determine the package name from the pylons.config object
        pkg_name = pylons.config['pylons.package']

        # Start the rest of our imports now that the app is loaded
        if is_minimal_template(pkg_name, True):
            model_module = None
            helpers_module = pkg_name + '.helpers'
            base_module = pkg_name + '.controllers'
        else:
            model_module = pkg_name + '.model'
            helpers_module = pkg_name + '.lib.helpers'
            base_module = pkg_name + '.lib.base'

        if model_module and can_import(model_module):
            locs['model'] = sys.modules[model_module]

        if can_import(helpers_module):
            locs['h'] = sys.modules[helpers_module]

        exec ('from pylons import app_globals, c, config, g, request, '
              'response, session, tmpl_context, url') in locs
        exec ('from pylons.controllers.util import abort, redirect_to') in locs
        exec 'from pylons.i18n import _, ungettext, N_' in locs
        exec 'from pylons.templating import render' in locs
        
        # Import all objects from the base module
        __import__(base_module)

        base = sys.modules[base_module]
        base_public = [__name for __name in dir(base) if not \
                       __name.startswith('_') or __name == '_']
        for name in base_public:
            locs[name] = getattr(base, name)
        locs.update(dict(wsgiapp=wsgiapp, app=test_app))

        mapper = tresponse.config.get('routes.map')
        if mapper:
            locs['mapper'] = mapper

        banner = "  All objects from %s are available\n" % base_module
        banner += "  Additional Objects:\n"
        if mapper:
            banner += "  %-10s -  %s\n" % ('mapper', 'Routes mapper object')
        banner += "  %-10s -  %s\n" % ('wsgiapp',
            "This project's WSGI App instance")
        banner += "  %-10s -  %s\n" % ('app',
            'paste.fixture wrapped around wsgiapp')

        try:
            if self.options.disable_ipython:
                raise ImportError()

            # try to use IPython if possible
            from IPython.Shell import IPShellEmbed

            shell = IPShellEmbed(argv=self.args)
            shell.set_banner(shell.IP.BANNER + '\n\n' + banner)
            try:
                shell(local_ns=locs, global_ns={})
            finally:
                paste.registry.restorer.restoration_end()
        except ImportError:
            import code
            py_prefix = sys.platform.startswith('java') and 'J' or 'P'
            newbanner = "Pylons Interactive Shell\n%sython %s\n\n" % \
                (py_prefix, sys.version)
            banner = newbanner + banner
            shell = code.InteractiveConsole(locals=locs)
            try:
                import readline
            except ImportError:
                pass
            try:
                shell.interact(banner)
            finally:
                paste.registry.restorer.restoration_end()
