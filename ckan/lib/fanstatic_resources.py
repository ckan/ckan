# encoding: utf-8

import os.path
import sys
import logging

from six.moves.configparser import RawConfigParser

from ckan.common import config

from fanstatic import Library, Resource, Group, get_library_registry
import fanstatic.core as core

# This imports patches fanstatic
import ckan.lib.fanstatic_extensions as fanstatic_extensions

log = logging.getLogger(__name__)


def min_path(path):
    '''Return the .min.* filename for the given .js or .css file.

    For example moo.js -> moo.min.js

    '''
    path, ext = os.path.splitext(path)
    return path + '.min' + ext


def create_library(name, path, depend_base=True):
    ''' Creates a fanstatic library `name` with the contents of a
    directory `path` using resource.config if found.'''

    def get_resource(lib_name, resource_name):
        ''' Attempt to get the resource from the current lib or if not try
        assume it is a fully qualified resource name. '''
        try:
            res = getattr(module, '%s/%s' % (lib_name, resource_name))
        except AttributeError:
            res = getattr(module, '%s' % resource_name)
        return res

    def create_resource(path, lib_name, count, inline=False, supersedes=None):
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
            core.set_resource_file_existence_checking(True)
        else:
            # This doesn't exist so stop fanstatic checking the filesystem
            if path not in force_top:
                kw['bottom'] = True
            core.set_resource_file_existence_checking(False)
        dependencies = []
        if path in depends:
            for dependency in depends[path]:
                dependencies.append(get_resource(name, dependency))
        if depend_base:
            dependencies.append(getattr(module, 'base/main'))
        if dependencies:
            kw['depends'] = dependencies
        if path in dont_bundle:
            kw['dont_bundle'] = True
        # IE conditionals
        condition = None
        other_browsers = False
        if path in IE_conditionals:
            other_browsers = ('others' in IE_conditionals[path])
            condition = IE_conditionals[path][0]
        if inline or condition:
            kw['renderer'] = fanstatic_extensions.CkanCustomRenderer(
                condition=condition,
                script=inline,
                renderer=renderer,
                other_browsers=other_browsers)
        if supersedes:
            superseded_library, superseded_resource_path = supersedes
            for _library in get_library_registry().values():
                if _library.name == superseded_library:
                    kw['supersedes'] = [_library.known_resources[superseded_resource_path]]
                    break
        resource = Resource(library, path, **kw)

        # Add our customised ordering
        if path in custom_render_order:
            resource.order = custom_render_order[path]
        resource.custom_order = count
        # Update the attributes of the minified version of the resource to
        # that of the parents as fanstatic does not pass these on.
        update_attributes = ['custom_order', 'order', 'bottom', 'depends',
                             'dont_bundle', 'renderer']
        if 'minified' in resource.modes:
            min_res = resource.modes['minified']
            for attribute in update_attributes:
                setattr(min_res, attribute, getattr(resource, attribute))

        # add the resource to this module
        fanstatic_name = '%s/%s' % (lib_name, path)
        setattr(module, fanstatic_name, resource)
        return resource

    resource_path = os.path.join(os.path.dirname(__file__), path)
    library = Library(name, path)
    module = sys.modules[__name__]

    # config options
    order = []
    dont_bundle = []
    force_top = []
    depends = {}
    groups = {}
    IE_conditionals = {}
    custom_render_order = {}
    inline_scripts = {}
    supersedes = {}

    # parse the resource.config file if it exists
    config_path = os.path.join(resource_path, 'resource.config')
    if os.path.exists(config_path):
        config = RawConfigParser()
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
        if config.has_section('supersedes'):
            items = config.items('supersedes')
            supersedes = dict((n, v.split('/', 1)) for (n, v) in items)

    # add dependencies for resources in groups
    for group in groups:
        if group in depends:
            for resource in groups[group]:
                if resource not in depends:
                    depends[resource] = []
                for dep in depends[group]:
                    if dep not in groups:
                        dep_resources = [dep]
                    else:
                        dep_resources = groups[dep]
                    diff = [
                        res for res in dep_resources if res not in depends[resource]]
                    depends[resource].extend(diff)

    # process each .js/.css file found
    resource_list = []
    for dirname, dirnames, filenames in os.walk(resource_path):
        for f in filenames:
            rel_path = dirname[len(path):]
            if rel_path:
                rel_path = rel_path[1:]
            filepath = os.path.join(rel_path, f)
            filename_only, extension = os.path.splitext(f)
            if extension in ('.css', '.js') and (
                    not filename_only.endswith('.min')):
                resource_list.append(filepath)

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

    # add inline scripts
    for inline in inline_scripts:
        resource_list.append(inline)
        if inline not in custom_render_order:
            custom_render_order[inline] = 20

    # order resource_list so that resources are created in the correct order
    for resource_name in reversed(order):
        if resource_name in resource_list:
            resource_list.remove(resource_name)
            resource_list.insert(0, resource_name)

    # create the resources and keep them ordered as we define them.
    count = 0
    for resource_name in resource_list:
        if resource_name in inline_scripts:
            inline = inline_scripts[resource_name].strip()
        else:
            inline = None
        create_resource(resource_name, name, count, inline=inline,
                        supersedes=supersedes.get(resource_name))
        count += 1

    # add groups
    for group_name in groups:
        members = []
        for member in groups[group_name]:
            fanstatic_name = '%s/%s' % (name, member)
            members.append(getattr(module, fanstatic_name))
        group = Group(members)
        fanstatic_name = '%s/%s' % (name, group_name)
        setattr(module, fanstatic_name, group)

    # finally add the library to this module
    setattr(module, name, library)
    # add to fanstatic
    registry = get_library_registry()
    registry.add(library)


public = config.get('ckan.base_public_folder')

base_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', public, 'base'))

log.debug('Base path {0}'.format(base_path))
create_library('vendor', os.path.join(base_path, 'vendor'), depend_base=False)

create_library('base', os.path.join(base_path, 'javascript'),
               depend_base=False)

create_library('datapreview', os.path.join(base_path, 'datapreview'),
               depend_base=False)

create_library('css', os.path.join(base_path, 'css'), depend_base=False)
