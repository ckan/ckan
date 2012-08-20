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

# This imports patches fanstatic
import ckan.lib.fanstatic_extensions as fanstatic_extensions

from ckan.include.rjsmin import jsmin
from ckan.include.rcssmin import cssmin

log = logging.getLogger(__name__)


def create_library(name, path, depend_base=True):
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
        log.debug('minified %s' % path)

    def create_resource(path, lib_name, count, inline=False):
        ''' create the fanstatic Resource '''
        renderer = None
        kw = {}
        if not inline:
            # resource_name is name of the file without the .js/.css
            rel_path, filename = os.path.split(path)
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
        else:
            kw['fake_resource'] = True
        dependencies = []
        if path in depends:
            for dependency in depends[path]:
                try:
                    res = getattr(module, '%s/%s' % (name, dependency))
                except AttributeError:
                    res = getattr(module, '%s' % dependency)
                dependencies.append(res)
        if depend_base:
            dependencies.append(getattr(module, 'base/main'))

        if dependencies:
            kw['depends'] = dependencies
        if path in dont_bundle:
            kw['dont_bundle'] = True
        if path in custom_render_order:
            kw['custom_renderer_order'] = custom_render_order[path]
        kw['custom_order'] = count
        # IE conditionals
        condition = None
        other_browsers = False
        if path in IE_conditionals:
            other_browsers = ('others' in IE_conditionals[path])
            condition = IE_conditionals[path][0]
        if inline:
            kw['renderer'] = fanstatic_extensions.InlineJSRenderer(
                                        condition=condition,
                                        script=inline,
                                        renderer=renderer,
                                        other_browsers=other_browsers)
        elif condition:
            kw['renderer'] = fanstatic_extensions.IEConditionalRenderer(
                                        condition=condition,
                                        renderer=renderer,
                                        other_browsers=other_browsers)
        resource = Resource(library, path, **kw)
        # add the resource to this module
        fanstatic_name = '%s/%s' % (lib_name, path)
        log.debug('create resource %s' % fanstatic_name)
        setattr(module, fanstatic_name, resource)
        return resource

    order = []
    dont_bundle = []
    force_top = []
    depends = {}
    groups = {}
    IE_conditionals = {}
    custom_render_order = {}
    inline_scripts = {}

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
        if config.has_section('inline scripts'):
            items = config.items('inline scripts')
            inline_scripts = dict((n, v) for (n, v) in items)
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
                # make sure any dependencies are met when we get to creating
                # the resource
                if resource in depends:
                    for dep in depends[resource]:
                        if dep not in order:
                            order.append(dep)
                order.append(resource)

    for x in reversed(order):
        if x in file_list:
            file_list.remove(x)
            file_list.insert(0, x)
    count = 0
    for f in file_list:
        create_resource(f, name, count)
        count += 1

    #inline scripts
    for inline in inline_scripts:
        create_resource(inline, name, count, inline=inline_scripts[inline].strip())
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

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                         '..', 'public', 'base'))
create_library('vendor', os.path.join(base_path, 'vendor'), depend_base=False)

create_library('datapreview', os.path.join(base_path, 'datapreview'), depend_base=False)

create_library('base', os.path.join(base_path, 'javascript'), depend_base=False)

create_library('css', os.path.join(base_path, 'css'), depend_base=False)
