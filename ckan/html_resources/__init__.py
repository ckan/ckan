import os.path
import sys
import ConfigParser

from fanstatic import Library, Resource

from ckan.include.rjsmin import jsmin
from ckan.include.rcssmin import cssmin

# TODO
# loop through dirs to setup
# warn on no entry point provided for fanstatic

def setup(name, path):

    def min_path(path):
        ''' return the .min filename eg moo.js -> moo.min.js '''
        if f.endswith('.js'):
            return path[:-3] + '.min.js'
        if f.endswith('.css'):
            return path[:-4] + '.min.css'

    def minify(filename, min_function):
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
        print 'minified %s' % path

    def create_resource(filename):
        ''' create the fanstatic Resource '''
        # resource_name is name of the file without the .js/.css
        resource_name = '.'.join(filename.split('.')[:-1])
        kw = {}
        path_min = min_path(os.path.join(resource_path, filename))
        if os.path.exists(path_min):
            kw['minified'] = min_path(filename)
        if filename.endswith('.js'):
            kw['bottom'] = True
        if resource_name in depends:
            dependencies = []
            for dependency in depends[resource_name]:
                dependencies.append(getattr(module, dependency))
            kw['depends'] = dependencies
        if resource_name in dont_bundle:
            kw['dont_bundle'] = True

        resource = Resource(library, filename, **kw)
        # add the resource to this module
        setattr(module, resource_name, resource)

    order = []
    dont_bundle = []
    depends = {}

    # parse the config.ini file if it exists
    resource_path = os.path.dirname(__file__)
    resource_path = os.path.join(resource_path, path)
    config_path = os.path.join(resource_path, 'config.ini')
    if os.path.exists(config_path):
        config = ConfigParser.RawConfigParser()
        config.read(config_path)
        if config.has_option('main', 'order'):
            order = config.get('main', 'order').split()
        if config.has_option('main', 'dont_bundle'):
            dont_bundle = config.get('main', 'dont_bundle').split()
        if config.has_section('depends'):
            items = config.items('depends')
            depends = dict((n, v.split()) for (n, v) in items)

    library = Library(name, path)
    module = sys.modules[__name__]

    # process each .js/.css file found
    for dirname, dirnames, filenames in os.walk(resource_path):
        for x in reversed(order):
            if x in filenames:
                filenames.remove(x)
                filenames.insert(0, x)
        for f in filenames:
            if f.endswith('.js') and not f.endswith('.min.js'):
                minify(f, jsmin)
                create_resource(f)
            if f.endswith('.css') and not f.endswith('.min.css'):
                minify(f, cssmin)
                create_resource(f)
    # finally add the library to this module
    setattr(module, name, library)


setup('resources', 'resources')
