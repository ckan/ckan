import fanstatic.core as core


class CkanCustomRenderer(object):
    ''' Allows for in-line js and IE conditionals via fanstatic. '''
    def __init__(self, script=None, renderer=None, condition=None,
                 other_browsers=False):
        self.script = script
        self.other_browsers = other_browsers
        self.renderer = renderer
        start = ''
        end = ''
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
    return '<script src="%s"></script>' % (url,)

#    __  __             _                ____       _       _
#   |  \/  | ___  _ __ | | _____ _   _  |  _ \ __ _| |_ ___| |__
#   | |\/| |/ _ \| '_ \| |/ / _ \ | | | | |_) / _` | __/ __| '_ \
#   | |  | | (_) | | | |   <  __/ |_| | |  __/ (_| | || (__| | | |
#   |_|  |_|\___/|_| |_|_|\_\___|\__, | |_|   \__,_|\__\___|_| |_|
#                                |___/

def render(self, library_url):

    paths = [resource.relpath for resource in self._resources]

    # MONKEY PATCH
    # We have changed the relpath to just use the bundle path as we don't
    # care about the dir name of the resource as that is now part of the
    # resource name.  We need this so that we can actually get to all the
    # resources regardless of the actual directory they are in.

    # relpath = ''.join([self.dirname, BUNDLE_PREFIX, ';'.join(paths)])
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

            # MONKEY PATCH
            # We allow .js files to be bundled even if they are in different
            # directories as the directory location doesn't actually matter
            # to javascript files just css files.
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
            resource.custom_order,  # Added in MONKEY PATCH
            resource.dependency_nr,
            resource.relpath)
    return sorted(resources, key=key)

core.sort_resources = sort_resources
