''' This file creates fanstatic resources from the sub directories. The
directory can contain a resource.config to specify how the resources should
be treated. minified copies of the resources are created if the resource
has a later modification time than existing minified versions.

NOTE :currently each library requires its entry point adding to the main
ckan setup.py file.


resource.config (example)
==========
# all resources are named without their file extension
[main]
# dont_bundle prevents the resources from being bundled
dont_bundle = test1
# order can be used to prevent dependency errors to ensure that the
# needed resources are created first
order = test1 test2
[depends]
# resource dependencies can be specified here by listing dependent
# resources
test2 = test1
[groups]
# a group containing several resources can be specified here
test3 = test2 test1


'''
import os.path
import sys
import logging
import ConfigParser

from fanstatic import Library, Resource, Group, get_library_registry
import fanstatic.core as core
from ckan.include.rjsmin import jsmin
from ckan.include.rcssmin import cssmin

log = logging.getLogger(__name__)

# TODO
# loop through dirs to setup
# warn on no entry point provided for fanstatic

class IEConditionalRenderer(object):
    ''' Allows for IE conditionals. '''
    def __init__(self, condition, renderer, other_browsers=False):
        self.condition = condition
        self.renderer = renderer
        self.other_browsers = other_browsers
        if other_browsers:
            self.other_browsers_start= '<!-->'
            self.other_browsers_end= '<!--'
        else:
            self.other_browsers_start= ''
            self.other_browsers_end= ''

    def __call__(self, url):
        return '<!--[if %s]>%s%s%s<![endif]-->' % (self.condition,
                                                   self.other_browsers_start,
                                                   self.renderer(url),
                                                   self.other_browsers_end)

# Fanstatic Patch #
# FIXME add full license info & push upstream
def __init__(self, library, relpath, **kw):

    depends = kw.get('depends', None)
    supersedes = kw.get('supersedes', None)
    bottom = kw.get('bottom', False)
    renderer = kw.get('renderer', None)
    dont_bundle = kw.get('dont_bundle', False)
    custom_renderer_order = kw.get('custom_renderer_order', None)
    custom_order = kw.get('custom_order', 0)

    # we don't want to pass these again
    minified = kw.pop('minified', None)
    debug = kw.pop('debug', None)

    self.library = library
    fullpath = os.path.normpath(os.path.join(library.path, relpath))
    if core._resource_file_existence_checking and not os.path.exists(fullpath):
        raise core.UnknownResourceError("Resource file does not exist: %s" %
                                   fullpath)
    self.relpath = relpath
    self.dirname, self.filename = os.path.split(relpath)
    if self.dirname and not self.dirname.endswith('/'):
        self.dirname += '/'
    self.bottom = bottom
    self.dont_bundle = dont_bundle
    self.custom_order = custom_order

    self.ext = os.path.splitext(self.relpath)[1]
    if renderer is None:
        # No custom, ad-hoc renderer for this Resource, so lookup
        # the default renderer by resource filename extension.
        if self.ext not in core.inclusion_renderers:
            raise core.UnknownResourceExtensionError(
                "Unknown resource extension %s for resource: %s" %
                (self.ext, repr(self)))
        self.order, self.renderer = core.inclusion_renderers[self.ext]
    else:
        # Use the custom renderer.
        self.renderer = renderer
        # If we do not know about the filename extension inclusion
        # order, we render the resource after all others.
        self.order, _ = core.inclusion_renderers.get(
            self.ext, (sys.maxint, None))

    if custom_renderer_order:
        self.order = custom_renderer_order
    assert not isinstance(depends, basestring)
    self.depends = set()
    if depends is not None:
        # Normalize groups into the underlying resources...
        depends = core.normalize_groups(depends)
        # ...before updating the set of dependencies of this resource.
        self.depends.update(depends)

    self.resources = set([self])
    for depend in self.depends:
        self.resources.update(depend.resources)

    # Check for library dependency cycles.
    self.library.check_dependency_cycle(self)

    # generate an internal number for sorting the resource
    # on dependency within the library
    self.init_dependency_nr()

    self.modes = {}
    for mode_name, argument in [(core.DEBUG, debug), (core.MINIFIED, minified)]:
        if argument is None:
            continue
        elif isinstance(argument, basestring):
            mode_resource = Resource(library, argument, **kw)
        else:
            # The dependencies of a mode resource should be the same
            # or a subset of the dependencies this mode replaces.
            if len(argument.depends - self.depends) > 0:
                raise core.ModeResourceDependencyError
            mode_resource = argument

        mode_resource.dependency_nr = self.dependency_nr
        self.modes[mode_name] = mode_resource

    assert not isinstance(supersedes, basestring)
    self.supersedes = supersedes or []

    self.rollups = []
    # create a reference to the superseder in the superseded resource
    for resource in self.supersedes:
        resource.rollups.append(self)
    # also create a reference to the superseding mode in the superseded
    # mode
    # XXX what if mode is full-fledged resource which lists
    # supersedes itself?
    for mode_name, mode in self.modes.items():
        for resource in self.supersedes:
            superseded_mode = resource.mode(mode_name)
            # if there is no such mode, let's skip it
            if superseded_mode is resource:
                continue
            mode.supersedes.append(superseded_mode)
            superseded_mode.rollups.append(mode)


    # Register ourself with the Library.
    self.library.register(self)

core.Resource.__init__ = __init__

def render(self, library_url):


    paths = [resource.relpath for resource in self._resources]
    # URL may become too long:
    # http://www.boutell.com/newfaq/misc/urllength.html
    relpath = ''.join([core.BUNDLE_PREFIX, ';'.join(paths)])

    return self.renderer('%s/%s' % (library_url, relpath))

core.Bundle.render = render
def fits(self, resource):
    if resource.dont_bundle:
        return False
    # an empty resource fits anything
    if not self._resources:
        return True
    # a resource fits if it's like the resources already inside
    bundle_resource = self._resources[0]
    return (resource.library is bundle_resource.library and
            resource.renderer is bundle_resource.renderer and
            (resource.ext == '.js' or
             resource.dirname == bundle_resource.dirname))

core.Bundle.fits = fits

def sort_resources(resources):
    """Sort resources for inclusion on web page.

    A number of rules are followed:

    * resources are always grouped per renderer (.js, .css, etc)
    * resources that depend on other resources are sorted later
    * resources are grouped by library, if the dependencies allow it
    * libraries are sorted by name, if dependencies allow it
    * resources are sorted by resource path if they both would be
      sorted the same otherwise.

    The only purpose of sorting on library is so we can
    group resources per library, so that bundles can later be created
    of them if bundling support is enabled.

    Note this sorting algorithm guarantees a consistent ordering, no
    matter in what order resources were needed.
    """
    for resource in resources:
        resource.library.init_library_nr()

    def key(resource):
        return (
            resource.order,
            resource.library.library_nr,
            resource.library.name,
            resource.custom_order,
            resource.dependency_nr,
            resource.renderer,
            resource.relpath)
    return sorted(resources, key=key)

core.sort_resources = sort_resources
# Fanstatic Patch #

def create_library(name, path):
    ''' Creates a fanstatic library `name` with the contents of a
    directory `path` using resource.config if found. Files are minified
    if needed. '''

    def min_path(path):
        ''' return the .min filename eg moo.js -> moo.min.js '''
        if f.endswith('.js'):
            return path[:-3] + '.min.js'
        if f.endswith('.css'):
            return path[:-4] + '.min.css'

    def minify(filename, resource_path, min_function):
        ''' Minify file path using min_function. '''
        # if the minified file was modified after the source file we can
        # assume that it is up-to-date
        path = os.path.join(resource_path, filename)
        path_min = min_path(path)
        op = os.path
        if op.exists(path_min) and op.getmtime(path) < op.getmtime(path_min):
            return
        source = open(path, 'r').read()
        f = open(path_min, 'w')
        f.write(min_function(source))
        f.close()
        log.info('minified %s' % path)

    def create_resource(path, lib_name, count):
        ''' create the fanstatic Resource '''
        # resource_name is name of the file without the .js/.css
        rel_path, filename = os.path.split(path)
        kw = {}
        filename = os.path.join(rel_path, filename)
        path_min = min_path(os.path.join(resource_path, filename))
        if os.path.exists(path_min):
            kw['minified'] = min_path(filename)
        if filename.endswith('.js'):
            renderer = core.render_js
            if path not in force_top:
                kw['bottom'] = True
        if filename.endswith('.css'):
            renderer = core.render_css
        if path in depends:
            dependencies = []
            for dependency in depends[path]:
                try:
                    res = getattr(module, '%s/%s' % (name, dependency))
                except AttributeError:
                    res = getattr(module, '%s' % dependency)
                dependencies.append(res)
            kw['depends'] = dependencies
        if path in dont_bundle:
            kw['dont_bundle'] = True
        if path in custom_render_order:
            kw['custom_renderer_order'] = custom_render_order[path]
        kw['custom_order'] = count
        # FIXME needs resource.config options enabled
        if path in IE_conditionals:
            other_browsers = ('others' in IE_conditionals[path])
            condition = IE_conditionals[path][0]
            kw['renderer'] = IEConditionalRenderer(
                                        condition=condition,
                                        renderer=renderer,
                                        other_browsers=other_browsers)
        resource = Resource(library, filename, **kw)
        # add the resource to this module
        fanstatic_name = '%s/%s' % (lib_name, filename)
        log.info('create resource %s' % fanstatic_name)
        setattr(module, fanstatic_name, resource)
        return resource

    order = []
    dont_bundle = []
    force_top = []
    depends = {}
    groups = {}
    IE_conditionals = {}
    custom_render_order = {}

    # parse the resource.config file if it exists
    resource_path = os.path.dirname(__file__)
    resource_path = os.path.join(resource_path, path)
    config_path = os.path.join(resource_path, 'resource.config')
    if os.path.exists(config_path):
        config = ConfigParser.RawConfigParser()
        config.read(config_path)
        if config.has_option('main', 'order'):
            order = config.get('main', 'order').split()
        if config.has_option('main', 'dont_bundle'):
            dont_bundle = config.get('main', 'dont_bundle').split()
        if config.has_option('main', 'force_top'):
            force_top = config.get('main', 'force_top').split()
        if config.has_section('depends'):
            items = config.items('depends')
            depends = dict((n, v.split()) for (n, v) in items)
        if config.has_section('groups'):
            items = config.items('groups')
            groups = dict((n, v.split()) for (n, v) in items)
        if config.has_section('custom render order'):
            items = config.items('custom render order')
            custom_render_order = dict((n, int(v)) for (n, v) in items)
        if config.has_section('IE conditional'):
            items = config.items('IE conditional')
            for (n, v) in items:
                files = v.split()
                for f in files:
                    if f not in IE_conditionals:
                        IE_conditionals[f] = []
                    IE_conditionals[f].append(n)


    for group in groups:
        if group in depends:
            for resource in groups[group]:
                if resource not in depends:
                    depends[resource] = []
                for dep in depends[group]:
                    if dep not in depends[resource]:
                        depends[resource].append(dep)

    library = Library(name, path)
    module = sys.modules[__name__]

    # process each .js/.css file found
    file_list = []
    for dirname, dirnames, filenames in os.walk(resource_path):
        for f in filenames:
            rel_path = dirname[len(path):]
            if rel_path:
                rel_path = rel_path[1:]
            filepath = os.path.join(rel_path, f)
            if f.endswith('.js') and not f.endswith('.min.js'):
                minify(f, dirname, jsmin)
                file_list.append(filepath)
            if f.endswith('.css') and not f.endswith('.min.css'):
                minify(f, dirname, cssmin)
                file_list.append(filepath)

    # if groups are defined make sure the order supplied there is honored
    for group in groups:
        for resource in groups[group]:
            if resource not in order:
                order.append(resource)

    for x in reversed(order):
        if x in file_list:
            file_list.remove(x)
            file_list.insert(0, x)
    count = 0
    for f in file_list:
        create_resource(f, name, count)
        count += 1

    # add groups
    for group_name in groups:
        members = []
        for member in groups[group_name]:
            fanstatic_name = '%s/%s' % (name, member)
            members.append(getattr(module, fanstatic_name))
        if group_name in depends:
            for dependency in depends[group_name]:
                try:
                    res = getattr(module, '%s/%s' % (name, dependency))
                except AttributeError:
                    res = getattr(module, '%s' % dependency)
                members = [res] + members #.append(res)
        group = Group(members)
        fanstatic_name = '%s/%s' % (name, group_name)
        setattr(module, fanstatic_name, group)
    # finally add the library to this module
    setattr(module, name, library)
    # add to fanstatic
    registry = get_library_registry()
    registry.add(library)

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'public', 'base', 'vendor'))
create_library('vendor', base_path)

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'public', 'base', 'datapreview'))
create_library('datapreview', base_path)

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'public', 'base', 'javascript'))
create_library('base', base_path)

### create our libraries here from any subdirectories
##for dirname, dirnames, filenames in os.walk(os.path.dirname(__file__)):
##    if dirname == os.path.dirname(__file__):
##        continue
##    lib_name = os.path.basename(dirname)
##    create_library(lib_name, lib_name)
