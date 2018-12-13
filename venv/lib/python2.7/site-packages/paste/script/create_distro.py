from __future__ import print_function
# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
import fnmatch
import os
import re
import sys

import pkg_resources

from . import copydir
from . import pluginlib
from .command import Command, BadCommand

class CreateDistroCommand(Command):

    usage = 'PACKAGE_NAME [VAR=VALUE VAR2=VALUE2 ...]'
    summary = "Create the file layout for a Python distribution"
    short_description = summary

    description = """\
    Create a new project.  Projects are typically Python packages,
    ready for distribution.  Projects are created from templates, and
    represent different kinds of projects -- associated with a
    particular framework for instance.
    """

    parser = Command.standard_parser(
        simulate=True, no_interactive=True, quiet=True, overwrite=True)
    parser.add_option('-t', '--template',
                      dest='templates',
                      metavar='TEMPLATE',
                      action='append',
                      help="Add a template to the create process")
    parser.add_option('-o', '--output-dir',
                      dest='output_dir',
                      metavar='DIR',
                      default='.',
                      help="Write put the directory into DIR (default current directory)")
    parser.add_option('--svn-repository',
                      dest='svn_repository',
                      metavar='REPOS',
                      help="Create package at given repository location (this will create the standard trunk/ tags/ branches/ hierarchy)")
    parser.add_option('--list-templates',
                      dest='list_templates',
                      action='store_true',
                      help="List all templates available")
    parser.add_option('--list-variables',
                      dest="list_variables",
                      action="store_true",
                      help="List all variables expected by the given template (does not create a package)")
    parser.add_option('--inspect-files',
                      dest='inspect_files',
                      action='store_true',
                      help="Show where the files in the given (already created) directory came from (useful when using multiple templates)")
    parser.add_option('--config',
                      action='store',
                      dest='config',
                      help="Template variables file")

    _bad_chars_re = re.compile('[^a-zA-Z0-9_]')

    default_verbosity = 1
    default_interactive = 1

    def command(self):
        if self.options.list_templates:
            return self.list_templates()
        asked_tmpls = self.options.templates or ['basic_package']
        templates = []
        for tmpl_name in asked_tmpls:
            self.extend_templates(templates, tmpl_name)
        if self.options.list_variables:
            return self.list_variables(templates)
        if self.verbose:
            print('Selected and implied templates:')
            max_tmpl_name = max([len(tmpl_name) for tmpl_name, tmpl in templates])
            for tmpl_name, tmpl in templates:
                print('  %s%s  %s' % (
                    tmpl_name, ' '*(max_tmpl_name-len(tmpl_name)),
                    tmpl.summary))
            print()
        if not self.args:
            if self.interactive:
                dist_name = self.challenge('Enter project name')
            else:
                raise BadCommand('You must provide a PACKAGE_NAME')
        else:
            dist_name = self.args[0].lstrip(os.path.sep)

        templates = [tmpl for name, tmpl in templates]
        output_dir = os.path.join(self.options.output_dir, dist_name)

        pkg_name = self._bad_chars_re.sub('', dist_name.lower())
        vars = {'project': dist_name,
                'package': pkg_name,
                'egg': pluginlib.egg_name(dist_name),
                }
        vars.update(self.parse_vars(self.args[1:]))
        if self.options.config and os.path.exists(self.options.config):
            for key, value in self.read_vars(self.options.config).items():
                vars.setdefault(key, value)

        if self.verbose: # @@: > 1?
            self.display_vars(vars)

        if self.options.inspect_files:
            self.inspect_files(
                output_dir, templates, vars)
            return
        if not os.path.exists(output_dir):
            # We want to avoid asking questions in copydir if the path
            # doesn't exist yet
            copydir.all_answer = 'y'

        if self.options.svn_repository:
            self.setup_svn_repository(output_dir, dist_name)

        # First we want to make sure all the templates get a chance to
        # set their variables, all at once, with the most specialized
        # template going first (the last template is the most
        # specialized)...
        for template in templates[::-1]:
            vars = template.check_vars(vars, self)

        # Gather all the templates egg_plugins into one var
        egg_plugins = set()
        for template in templates:
            egg_plugins.update(template.egg_plugins)
        egg_plugins = sorted(egg_plugins)
        vars['egg_plugins'] = egg_plugins

        for template in templates:
            self.create_template(
                template, output_dir, vars)

        found_setup_py = False
        paster_plugins_mtime = None
        if os.path.exists(os.path.join(output_dir, 'setup.py')):
            # Grab paster_plugins.txt's mtime; used to determine if the
            # egg_info command wrote to it
            try:
                egg_info_dir = pluginlib.egg_info_dir(output_dir, dist_name)
            except IOError:
                egg_info_dir = None
            if egg_info_dir is not None:
                plugins_path = os.path.join(egg_info_dir, 'paster_plugins.txt')
                if os.path.exists(plugins_path):
                    paster_plugins_mtime = os.path.getmtime(plugins_path)

            self.run_command(sys.executable, 'setup.py', 'egg_info',
                             cwd=output_dir,
                             # This shouldn't be necessary, but a bug in setuptools 0.6c3 is causing a (not entirely fatal) problem that I don't want to fix right now:
                             expect_returncode=True)
            found_setup_py = True
        elif self.verbose > 1:
            print('No setup.py (cannot run egg_info)')

        package_dir = vars.get('package_dir', None)
        if package_dir:
            output_dir = os.path.join(output_dir, package_dir)

        # With no setup.py this doesn't make sense:
        if found_setup_py:
            # Only write paster_plugins.txt if it wasn't written by
            # egg_info (the correct way). leaving us to do it is
            # deprecated and you'll get warned
            egg_info_dir = pluginlib.egg_info_dir(output_dir, dist_name)
            plugins_path = os.path.join(egg_info_dir, 'paster_plugins.txt')
            if len(egg_plugins) and (not os.path.exists(plugins_path) or \
                    os.path.getmtime(plugins_path) == paster_plugins_mtime):
                if self.verbose:
                    print(('Manually creating paster_plugins.txt (deprecated! '
                         'pass a paster_plugins keyword to setup() instead)'), file=sys.stderr)
                for plugin in egg_plugins:
                    if self.verbose:
                        print('Adding %s to paster_plugins.txt' % plugin)
                    if not self.simulate:
                        pluginlib.add_plugin(egg_info_dir, plugin)

        if self.options.svn_repository:
            self.add_svn_repository(vars, output_dir)

        if self.options.config:
            write_vars = vars.copy()
            del write_vars['project']
            del write_vars['package']
            self.write_vars(self.options.config, write_vars)

    def create_template(self, template, output_dir, vars):
        if self.verbose:
            print('Creating template %s' % template.name)
        template.run(self, output_dir, vars)

    def setup_svn_repository(self, output_dir, dist_name):
        # @@: Use subprocess
        svn_repos = self.options.svn_repository
        svn_repos_path = os.path.join(svn_repos, dist_name).replace('\\','/')
        svn_command = 'svn'
        if sys.platform == 'win32':
            svn_command += '.exe'
        # @@: The previous method of formatting this string using \ doesn't work on Windows
        cmd = '%(svn_command)s mkdir %(svn_repos_path)s' + \
            ' %(svn_repos_path)s/trunk %(svn_repos_path)s/tags' + \
            ' %(svn_repos_path)s/branches -m "New project %(dist_name)s"'
        cmd = cmd % {
            'svn_repos_path': svn_repos_path,
            'dist_name': dist_name,
            'svn_command':svn_command,
        }
        if self.verbose:
            print("Running:")
            print(cmd)
        if not self.simulate:
            os.system(cmd)
        svn_repos_path_trunk = os.path.join(svn_repos_path,'trunk').replace('\\','/')
        cmd = svn_command+' co "%s" "%s"' % (svn_repos_path_trunk, output_dir)
        if self.verbose:
            print("Running %s" % cmd)
        if not self.simulate:
            os.system(cmd)

    ignore_egg_info_files = [
        'top_level.txt',
        'entry_points.txt',
        'requires.txt',
        'PKG-INFO',
        'namespace_packages.txt',
        'SOURCES.txt',
        'dependency_links.txt',
        'not-zip-safe']

    def add_svn_repository(self, vars, output_dir):
        svn_repos = self.options.svn_repository
        egg_info_dir = pluginlib.egg_info_dir(output_dir, vars['project'])
        svn_command = 'svn'
        if sys.platform == 'win32':
            svn_command += '.exe'
        self.run_command(svn_command, 'add', '-N', egg_info_dir)
        paster_plugins_file = os.path.join(
            egg_info_dir, 'paster_plugins.txt')
        if os.path.exists(paster_plugins_file):
            self.run_command(svn_command, 'add', paster_plugins_file)
        self.run_command(svn_command, 'ps', 'svn:ignore',
                         '\n'.join(self.ignore_egg_info_files),
                         egg_info_dir)
        if self.verbose:
            print ("You must next run 'svn commit' to commit the "
                   "files to repository")

    def extend_templates(self, templates, tmpl_name):
        if '#' in tmpl_name:
            dist_name, tmpl_name = tmpl_name.split('#', 1)
        else:
            dist_name, tmpl_name = None, tmpl_name
        if dist_name is None:
            for entry in self.all_entry_points():
                if entry.name == tmpl_name:
                    tmpl = entry.load()(entry.name)
                    dist_name = entry.dist.project_name
                    break
            else:
                raise LookupError(
                    'Template by name %r not found' % tmpl_name)
        else:
            dist = pkg_resources.get_distribution(dist_name)
            entry = dist.get_entry_info(
                'paste.paster_create_template', tmpl_name)
            tmpl = entry.load()(entry.name)
        full_name = '%s#%s' % (dist_name, tmpl_name)
        for item_full_name, item_tmpl in templates:
            if item_full_name == full_name:
                # Already loaded
                return
        for req_name in tmpl.required_templates:
            self.extend_templates(templates, req_name)
        templates.append((full_name, tmpl))

    def all_entry_points(self):
        if not hasattr(self, '_entry_points'):
            self._entry_points = list(pkg_resources.iter_entry_points(
            'paste.paster_create_template'))
        return self._entry_points

    def display_vars(self, vars):
        vars = sorted(vars.items())
        print('Variables:')
        max_var = max([len(n) for n, v in vars])
        for name, value in vars:
            print('  %s:%s  %s' % (
                name, ' '*(max_var-len(name)), value))

    def list_templates(self):
        templates = []
        for entry in self.all_entry_points():
            try:
                templates.append(entry.load()(entry.name))
            except Exception as e:
                # We will not be stopped!
                print('Warning: could not load entry point %s (%s: %s)' % (
                    entry.name, e.__class__.__name__, e))
        max_name = max([len(t.name) for t in templates])
        templates = sorted(templates, key=lambda a: a.name)
        print('Available templates:')
        for template in templates:
            # @@: Wrap description
            print('  %s:%s  %s' % (
                template.name,
                ' '*(max_name-len(template.name)),
                template.summary))

    def inspect_files(self, output_dir, templates, vars):
        file_sources = {}
        for template in templates:
            self._find_files(template, vars, file_sources)
        self._show_files(output_dir, file_sources)
        self._show_leftovers(output_dir, file_sources)

    def _find_files(self, template, vars, file_sources):
        tmpl_dir = template.template_dir()
        self._find_template_files(
            template, tmpl_dir, vars, file_sources)

    def _find_template_files(self, template, tmpl_dir, vars,
                             file_sources, join=''):
        full_dir = os.path.join(tmpl_dir, join)
        for name in os.listdir(full_dir):
            if name.startswith('.'):
                continue
            if os.path.isdir(os.path.join(full_dir, name)):
                self._find_template_files(
                    template, tmpl_dir, vars, file_sources,
                    join=os.path.join(join, name))
                continue
            partial = os.path.join(join, name)
            for name, value in vars.items():
                partial = partial.replace('+%s+' % name, value)
            if partial.endswith('_tmpl'):
                partial = partial[:-5]
            file_sources.setdefault(partial, []).append(template)

    _ignore_filenames = ['.*', '*.pyc', '*.bak*']
    _ignore_dirs = ['CVS', '_darcs', '.svn']

    def _show_files(self, output_dir, file_sources, join='', indent=0):
        pad = ' '*(2*indent)
        full_dir = os.path.join(output_dir, join)
        names = os.listdir(full_dir)
        dirs = [n for n in names
                if os.path.isdir(os.path.join(full_dir, n))]
        fns = [n for n in names
               if not os.path.isdir(os.path.join(full_dir, n))]
        dirs.sort()
        names.sort()
        for name in names:
            skip_this = False
            for ext in self._ignore_filenames:
                if fnmatch.fnmatch(name, ext):
                    if self.verbose > 1:
                        print('%sIgnoring %s' % (pad, name))
                    skip_this = True
                    break
            if skip_this:
                continue
            partial = os.path.join(join, name)
            if partial not in file_sources:
                if self.verbose > 1:
                    print('%s%s (not from template)' % (pad, name))
                continue
            templates = file_sources.pop(partial)
            print('%s%s from:' % (pad, name))
            for template in templates:
                print('%s  %s' % (pad, template.name))
        for dir in dirs:
            if dir in self._ignore_dirs:
                continue
            print('%sRecursing into %s/' % (pad, dir))
            self._show_files(
                output_dir, file_sources,
                join=os.path.join(join, dir),
                indent=indent+1)

    def _show_leftovers(self, output_dir, file_sources):
        if not file_sources:
            return
        print()
        print('These files were supposed to be generated by templates')
        print('but were not found:')
        file_sources = sorted(file_sources.items())
        for partial, templates in file_sources:
            print('  %s from:' % partial)
            for template in templates:
                print('    %s' % template.name)

    def list_variables(self, templates):
        for tmpl_name, tmpl in templates:
            if not tmpl.read_vars():
                if self.verbose > 1:
                    self._show_template_vars(
                        tmpl_name, tmpl, 'No variables found')
                continue
            self._show_template_vars(tmpl_name, tmpl)

    def _show_template_vars(self, tmpl_name, tmpl, message=None):
        title = '%s (from %s)' % (tmpl.name, tmpl_name)
        print(title)
        print('-'*len(title))
        if message is not None:
            print('  %s' % message)
            print()
            return
        tmpl.print_vars(indent=2)
