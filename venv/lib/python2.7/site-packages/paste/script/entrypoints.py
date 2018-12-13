from __future__ import print_function
# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
import textwrap
import os
import pkg_resources
from .command import Command, BadCommand
import fnmatch
import re
import traceback
import six
from six.moves import cStringIO as StringIO
import inspect
import types

class EntryPointCommand(Command):

    usage = "ENTRY_POINT"
    summary = "Show information about entry points"

    description = """\
    Shows information about one or many entry points (you can use
    wildcards for entry point names).  Entry points are used for Egg
    plugins, and are named resources -- like an application, template
    plugin, or other resource.  Entry points have a [group] which
    defines what kind of object they describe, and inside groups each
    entry point is named.
    """

    max_args = 2

    parser = Command.standard_parser(verbose=False)
    parser.add_option('--list', '-l',
                      dest='list_entry_points',
                      action='store_true',
                      help='List all the kinds of entry points on the system')
    parser.add_option('--egg', '-e',
                      dest='show_egg',
                      help="Show all the entry points for the given Egg")
    parser.add_option('--regex',
                      dest='use_regex',
                      action='store_true',
                      help="Make pattern match as regular expression, not just a wildcard pattern")

    def command(self):
        if self.options.list_entry_points:
            return self.list_entry_points()
        if self.options.show_egg:
            return self.show_egg(self.options.show_egg)
        if not self.args:
            raise BadCommand("You must give an entry point (or --list)")
        pattern = self.get_pattern(self.args[0])
        groups = self.get_groups_by_pattern(pattern)
        if not groups:
            raise BadCommand('No group matched %s' % self.args[0])
        ep_pat = None
        if len(self.args) > 1:
            ep_pat = self.get_pattern(self.args[1])
        for group in groups:
            desc = self.get_group_description(group)
            print('[%s]' % group)
            if desc:
                print(self.wrap(desc))
                print()
            self.print_entry_points_by_group(group, ep_pat)

    def print_entry_points_by_group(self, group, ep_pat):
        env = pkg_resources.Environment()
        project_names = sorted(env)
        for project_name in project_names:
            dists = list(env[project_name])
            assert dists
            dist = dists[0]
            entries = list(dist.get_entry_map(group).values())
            if ep_pat:
                entries = [e for e in entries
                           if ep_pat.search(e.name)]
            if not entries:
                continue
            if len(dists) > 1:
                print('%s (+ %i older versions)' % (
                    dist, len(dists)-1))
            else:
                print('%s' % dist)
            entries.sort(key=lambda entry: entry.name)
            for entry in entries:
                print(self._ep_description(entry))
                desc = self.get_entry_point_description(entry, group)
                if desc and desc.description:
                    print(self.wrap(desc.description, indent=4))

    def show_egg(self, egg_name):
        group_pat = None
        if self.args:
            group_pat = self.get_pattern(self.args[0])
        ep_pat = None
        if len(self.args) > 1:
            ep_pat = self.get_pattern(self.args[1])
        if egg_name.startswith('egg:'):
            egg_name = egg_name[4:]
        dist = pkg_resources.get_distribution(egg_name)
        entry_map = dist.get_entry_map()
        entry_groups = sorted(entry_map.items())
        for group, points in entry_groups:
            if group_pat and not group_pat.search(group):
                continue
            print('[%s]' % group)
            points = sorted(points.items())
            for name, entry in points:
                if ep_pat:
                    if not ep_pat.search(name):
                        continue
                print(self._ep_description(entry))
                desc = self.get_entry_point_description(entry, group)
                if desc and desc.description:
                    print(self.wrap(desc.description, indent=2))
                print()

    def wrap(self, text, indent=0):
        text = dedent(text)
        width = int(os.environ.get('COLUMNS', 70)) - indent
        text = '\n'.join([line.rstrip() for line in text.splitlines()])
        paras = text.split('\n\n')
        new_paras = []
        for para in paras:
            if para.lstrip() == para:
                # leading whitespace means don't rewrap
                para = '\n'.join(textwrap.wrap(para, width))
            new_paras.append(para)
        text = '\n\n'.join(new_paras)
        lines = [' '*indent + line
                 for line in text.splitlines()]
        return '\n'.join(lines)

    def _ep_description(self, ep, pad_name=None):
        name = ep.name
        if pad_name is not None:
            name = name + ' '*(pad_name-len(name))
        dest = ep.module_name
        if ep.attrs:
            dest = dest + ':' + '.'.join(ep.attrs)
        return '%s = %s' % (name, dest)

    def get_pattern(self, s):
        if not s:
            return None
        if self.options.use_regex:
            return re.compile(s)
        else:
            return re.compile(fnmatch.translate(s), re.I)

    def list_entry_points(self):
        pattern = self.get_pattern(self.args and self.args[0])
        groups = self.get_groups_by_pattern(pattern)
        print('%i entry point groups found:' % len(groups))
        for group in groups:
            desc = self.get_group_description(group)
            print('[%s]' % group)
            if desc:
                if hasattr(desc, 'description'):
                    desc = desc.description
                print(self.wrap(desc, indent=2))

    def get_groups_by_pattern(self, pattern):
        env = pkg_resources.Environment()
        eps = {}
        for project_name in env:
            for dist in env[project_name]:
                for name in pkg_resources.get_entry_map(dist):
                    if pattern and not pattern.search(name):
                        continue
                    if (not pattern
                        and name.startswith('paste.description.')):
                        continue
                    eps[name] = None
        return sorted(eps.keys())

    def get_group_description(self, group):
        for entry in pkg_resources.iter_entry_points('paste.entry_point_description'):
            if entry.name == group:
                ep = entry.load()
                if hasattr(ep, 'description'):
                    return ep.description
                else:
                    return ep
        return None

    def get_entry_point_description(self, ep, group):
        try:
            return self._safe_get_entry_point_description(ep, group)
        except Exception as e:
            out = StringIO()
            traceback.print_exc(file=out)
            return ErrorDescription(e, out.getvalue())

    def _safe_get_entry_point_description(self, ep, group):
        ep.dist.activate()
        meta_group = 'paste.description.'+group
        meta = ep.dist.get_entry_info(meta_group, ep.name)
        if not meta:
            generic = list(pkg_resources.iter_entry_points(
                meta_group, 'generic'))
            if not generic:
                return super_generic(ep.load())
            # @@: Error if len(generic) > 1?
            obj = generic[0].load()
            desc = obj(ep, group)
        else:
            desc = meta.load()
        return desc

class EntryPointDescription(object):

    def __init__(self, group):
        self.group = group

    # Should define:
    # * description

class SuperGeneric(object):

    def __init__(self, doc_object):
        self.doc_object = doc_object
        self.description = dedent(self.doc_object.__doc__)
        try:
            if isinstance(self.doc_object, type):
                func = six.get_unbound_function(self.doc_object.__init__)
            elif (hasattr(self.doc_object, '__call__')
                  and not isinstance(self.doc_object, types.FunctionType)):
                func = self.doc_object.__call__
            else:
                func = self.doc_object
            if hasattr(func, '__paste_sig__'):
                sig = func.__paste_sig__
            else:
                sig = inspect.getargspec(func)
                sig = inspect.formatargspec(*sig)
        except TypeError:
            sig = None
        if sig:
            if self.description:
                self.description = '%s\n\n%s' % (
                    sig, self.description)
            else:
                self.description = sig

def dedent(s):
    if s is None:
        return s
    s = s.strip('\n').strip('\r')
    return textwrap.dedent(s)

def super_generic(obj):
    desc = SuperGeneric(obj)
    if not desc.description:
        return None
    return desc

class ErrorDescription(object):

    def __init__(self, exc, tb):
        self.exc = exc
        self.tb = '\n'.join(tb)
        self.description = 'Error loading: %s' % exc

