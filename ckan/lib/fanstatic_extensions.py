import os.path
import sys

from fanstatic import Resource

import fanstatic.core as core

class IEConditionalRenderer(object):
    ''' Allows for IE conditionals. '''
    def __init__(self, condition, renderer, other_browsers=False):
        self.condition = condition
        self.renderer = renderer
        if other_browsers:
            self.other_browsers_start = '<!-->'
            self.other_browsers_end = '<!--'
        else:
            self.other_browsers_start = ''
            self.other_browsers_end = ''

    def __call__(self, url):
        return '<!--[if %s]>%s%s%s<![endif]-->' % (self.condition,
                                                   self.other_browsers_start,
                                                   self.renderer(url),
                                                   self.other_browsers_end)
class InlineJSRenderer(object):
    ''' Allows for in-line js via fanstatic. '''
    def __init__(self, script=None, renderer=None, condition=None, other_browsers=False):
        self.script = script
        self.other_browsers = other_browsers
        self.renderer = renderer
        start= ''
        end= ''
        # IE conditionals
        if condition:
            start = '<!--[if %s]>' % condition
            end = '<![endif]-->'
            if other_browsers:
                start += '<!-->'
                end = '<!--' + end
        self.start = start
        self.end = end

    def __call__(self, url):
        if self.script:
            return '%s<script>%s</script>%s' % (self.start,
                               self.script,
                               self.end)
        return '%s%s%s' % (self.start,
                           self.renderer(url),
                           self.end)
def render_js(url):
    return '<script type="text/javascript" src="%s"></script>' % (url,)

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
    if core._resource_file_existence_checking and not os.path.exists(fullpath) \
                                    and not kw.get('fake_resource', False):
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

    if custom_renderer_order is not None:
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
