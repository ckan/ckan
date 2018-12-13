# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
WSGI applications that parse the URL and dispatch to on-disk resources
"""

import os
import sys
import imp
import mimetypes
try:
    import pkg_resources
except ImportError:
    pkg_resources = None
from paste import request
from paste import fileapp
from paste.util import import_string
from paste import httpexceptions
from httpheaders import ETAG
from paste.util import converters

class NoDefault(object):
    pass

__all__ = ['URLParser', 'StaticURLParser', 'PkgResourcesParser']

class URLParser(object):

    """
    WSGI middleware

    Application dispatching, based on URL.  An instance of `URLParser` is
    an application that loads and delegates to other applications.  It
    looks for files in its directory that match the first part of
    PATH_INFO; these may have an extension, but are not required to have
    one, in which case the available files are searched to find the
    appropriate file.  If it is ambiguous, a 404 is returned and an error
    logged.

    By default there is a constructor for .py files that loads the module,
    and looks for an attribute ``application``, which is a ready
    application object, or an attribute that matches the module name,
    which is a factory for building applications, and is called with no
    arguments.

    URLParser will also look in __init__.py for special overrides.
    These overrides are:

    ``urlparser_hook(environ)``
        This can modify the environment.  Its return value is ignored,
        and it cannot be used to change the response in any way.  You
        *can* use this, for example, to manipulate SCRIPT_NAME/PATH_INFO
        (try to keep them consistent with the original URL -- but
        consuming PATH_INFO and moving that to SCRIPT_NAME is ok).

    ``urlparser_wrap(environ, start_response, app)``:
        After URLParser finds the application, it calls this function
        (if present).  If this function doesn't call
        ``app(environ, start_response)`` then the application won't be
        called at all!  This can be used to allocate resources (with
        ``try:finally:``) or otherwise filter the output of the
        application.

    ``not_found_hook(environ, start_response)``:
        If no file can be found (*in this directory*) to match the
        request, then this WSGI application will be called.  You can
        use this to change the URL and pass the request back to
        URLParser again, or on to some other application.  This
        doesn't catch all ``404 Not Found`` responses, just missing
        files.

    ``application(environ, start_response)``:
        This basically overrides URLParser completely, and the given
        application is used for all requests.  ``urlparser_wrap`` and
        ``urlparser_hook`` are still called, but the filesystem isn't
        searched in any way.
    """

    parsers_by_directory = {}

    # This is lazily initialized
    init_module = NoDefault

    global_constructors = {}

    def __init__(self, global_conf,
                 directory, base_python_name,
                 index_names=NoDefault,
                 hide_extensions=NoDefault,
                 ignore_extensions=NoDefault,
                 constructors=None,
                 **constructor_conf):
        """
        Create a URLParser object that looks at `directory`.
        `base_python_name` is the package that this directory
        represents, thus any Python modules in this directory will
        be given names under this package.
        """
        if global_conf:
            import warnings
            warnings.warn(
                'The global_conf argument to URLParser is deprecated; '
                'either pass in None or {}, or use make_url_parser',
                DeprecationWarning)
        else:
            global_conf = {}
        if os.path.sep != '/':
            directory = directory.replace(os.path.sep, '/')
        self.directory = directory
        self.base_python_name = base_python_name
        # This logic here should be deprecated since it is in
        # make_url_parser
        if index_names is NoDefault:
            index_names = global_conf.get(
                'index_names', ('index', 'Index', 'main', 'Main'))
        self.index_names = converters.aslist(index_names)
        if hide_extensions is NoDefault:
            hide_extensions = global_conf.get(
                'hide_extensions', ('.pyc', '.bak', '.py~', '.pyo'))
        self.hide_extensions = converters.aslist(hide_extensions)
        if ignore_extensions is NoDefault:
            ignore_extensions = global_conf.get(
                'ignore_extensions', ())
        self.ignore_extensions = converters.aslist(ignore_extensions)
        self.constructors = self.global_constructors.copy()
        if constructors:
            self.constructors.update(constructors)
        # @@: Should we also check the global options for constructors?
        for name, value in constructor_conf.items():
            if not name.startswith('constructor '):
                raise ValueError(
                    "Only extra configuration keys allowed are "
                    "'constructor .ext = import_expr'; you gave %r "
                    "(=%r)" % (name, value))
            ext = name[len('constructor '):].strip()
            if isinstance(value, (str, unicode)):
                value = import_string.eval_import(value)
            self.constructors[ext] = value

    def __call__(self, environ, start_response):
        environ['paste.urlparser.base_python_name'] = self.base_python_name
        if self.init_module is NoDefault:
            self.init_module = self.find_init_module(environ)
        path_info = environ.get('PATH_INFO', '')
        if not path_info:
            return self.add_slash(environ, start_response)
        if (self.init_module
            and getattr(self.init_module, 'urlparser_hook', None)):
            self.init_module.urlparser_hook(environ)
        orig_path_info = environ['PATH_INFO']
        orig_script_name = environ['SCRIPT_NAME']
        application, filename = self.find_application(environ)
        if not application:
            if (self.init_module
                and getattr(self.init_module, 'not_found_hook', None)
                and environ.get('paste.urlparser.not_found_parser') is not self):
                not_found_hook = self.init_module.not_found_hook
                environ['paste.urlparser.not_found_parser'] = self
                environ['PATH_INFO'] = orig_path_info
                environ['SCRIPT_NAME'] = orig_script_name
                return not_found_hook(environ, start_response)
            if filename is None:
                name, rest_of_path = request.path_info_split(environ['PATH_INFO'])
                if not name:
                    name = 'one of %s' % ', '.join(
                        self.index_names or
                        ['(no index_names defined)'])

                return self.not_found(
                    environ, start_response,
                    'Tried to load %s from directory %s'
                    % (name, self.directory))
            else:
                environ['wsgi.errors'].write(
                    'Found resource %s, but could not construct application\n'
                    % filename)
                return self.not_found(
                    environ, start_response,
                    'Tried to load %s from directory %s'
                    % (filename, self.directory))
        if (self.init_module
            and getattr(self.init_module, 'urlparser_wrap', None)):
            return self.init_module.urlparser_wrap(
                environ, start_response, application)
        else:
            return application(environ, start_response)

    def find_application(self, environ):
        if (self.init_module
            and getattr(self.init_module, 'application', None)
            and not environ.get('paste.urlparser.init_application') == environ['SCRIPT_NAME']):
            environ['paste.urlparser.init_application'] = environ['SCRIPT_NAME']
            return self.init_module.application, None
        name, rest_of_path = request.path_info_split(environ['PATH_INFO'])
        environ['PATH_INFO'] = rest_of_path
        if name is not None:
            environ['SCRIPT_NAME'] = environ.get('SCRIPT_NAME', '') + '/' + name
        if not name:
            names = self.index_names
            for index_name in names:
                filename = self.find_file(environ, index_name)
                if filename:
                    break
            else:
                # None of the index files found
                filename = None
        else:
            filename = self.find_file(environ, name)
        if filename is None:
            return None, filename
        else:
            return self.get_application(environ, filename), filename

    def not_found(self, environ, start_response, debug_message=None):
        exc = httpexceptions.HTTPNotFound(
            'The resource at %s could not be found'
            % request.construct_url(environ),
            comment=debug_message)
        return exc.wsgi_application(environ, start_response)

    def add_slash(self, environ, start_response):
        """
        This happens when you try to get to a directory
        without a trailing /
        """
        url = request.construct_url(environ, with_query_string=False)
        url += '/'
        if environ.get('QUERY_STRING'):
            url += '?' + environ['QUERY_STRING']
        exc = httpexceptions.HTTPMovedPermanently(
            'The resource has moved to %s - you should be redirected '
            'automatically.' % url,
            headers=[('location', url)])
        return exc.wsgi_application(environ, start_response)

    def find_file(self, environ, base_filename):
        possible = []
        """Cache a few values to reduce function call overhead"""
        for filename in os.listdir(self.directory):
            base, ext = os.path.splitext(filename)
            full_filename = os.path.join(self.directory, filename)
            if (ext in self.hide_extensions
                or not base):
                continue
            if filename == base_filename:
                possible.append(full_filename)
                continue
            if ext in self.ignore_extensions:
                continue
            if base == base_filename:
                possible.append(full_filename)
        if not possible:
            #environ['wsgi.errors'].write(
            #    'No file found matching %r in %s\n'
            #    % (base_filename, self.directory))
            return None
        if len(possible) > 1:
            # If there is an exact match, this isn't 'ambiguous'
            # per se; it might mean foo.gif and foo.gif.back for
            # instance
            if full_filename in possible:
                return full_filename
            else:
                environ['wsgi.errors'].write(
                    'Ambiguous URL: %s; matches files %s\n'
                    % (request.construct_url(environ),
                       ', '.join(possible)))
            return None
        return possible[0]

    def get_application(self, environ, filename):
        if os.path.isdir(filename):
            t = 'dir'
        else:
            t = os.path.splitext(filename)[1]
        constructor = self.constructors.get(t, self.constructors.get('*'))
        if constructor is None:
            #environ['wsgi.errors'].write(
            #    'No constructor found for %s\n' % t)
            return constructor
        app = constructor(self, environ, filename)
        if app is None:
            #environ['wsgi.errors'].write(
            #    'Constructor %s return None for %s\n' %
            #    (constructor, filename))
            pass
        return app

    def register_constructor(cls, extension, constructor):
        """
        Register a function as a constructor.  Registered constructors
        apply to all instances of `URLParser`.

        The extension should have a leading ``.``, or the special
        extensions ``dir`` (for directories) and ``*`` (a catch-all).

        `constructor` must be a callable that takes two arguments:
        ``environ`` and ``filename``, and returns a WSGI application.
        """
        d = cls.global_constructors
        assert not d.has_key(extension), (
            "A constructor already exists for the extension %r (%r) "
            "when attemption to register constructor %r"
            % (extension, d[extension], constructor))
        d[extension] = constructor
    register_constructor = classmethod(register_constructor)

    def get_parser(self, directory, base_python_name):
        """
        Get a parser for the given directory, or create one if
        necessary.  This way parsers can be cached and reused.

        # @@: settings are inherited from the first caller
        """
        try:
            return self.parsers_by_directory[(directory, base_python_name)]
        except KeyError:
            parser = self.__class__(
                {},
                directory, base_python_name,
                index_names=self.index_names,
                hide_extensions=self.hide_extensions,
                ignore_extensions=self.ignore_extensions,
                constructors=self.constructors)
            self.parsers_by_directory[(directory, base_python_name)] = parser
            return parser

    def find_init_module(self, environ):
        filename = os.path.join(self.directory, '__init__.py')
        if not os.path.exists(filename):
            return None
        return load_module(environ, filename)

    def __repr__(self):
        return '<%s directory=%r; module=%s at %s>' % (
            self.__class__.__name__,
            self.directory,
            self.base_python_name,
            hex(abs(id(self))))

def make_directory(parser, environ, filename):
    base_python_name = environ['paste.urlparser.base_python_name']
    if base_python_name:
        base_python_name += "." + os.path.basename(filename)
    else:
        base_python_name = os.path.basename(filename)
    return parser.get_parser(filename, base_python_name)

URLParser.register_constructor('dir', make_directory)

def make_unknown(parser, environ, filename):
    return fileapp.FileApp(filename)

URLParser.register_constructor('*', make_unknown)

def load_module(environ, filename):
    base_python_name = environ['paste.urlparser.base_python_name']
    module_name = os.path.splitext(os.path.basename(filename))[0]
    if base_python_name:
        module_name = base_python_name + '.' + module_name
    return load_module_from_name(environ, filename, module_name,
                                 environ['wsgi.errors'])

def load_module_from_name(environ, filename, module_name, errors):
    if sys.modules.has_key(module_name):
        return sys.modules[module_name]
    init_filename = os.path.join(os.path.dirname(filename), '__init__.py')
    if not os.path.exists(init_filename):
        try:
            f = open(init_filename, 'w')
        except (OSError, IOError), e:
            errors.write(
                'Cannot write __init__.py file into directory %s (%s)\n'
                % (os.path.dirname(filename), e))
            return None
        f.write('#\n')
        f.close()
    fp = None
    if sys.modules.has_key(module_name):
        return sys.modules[module_name]
    if '.' in module_name:
        parent_name = '.'.join(module_name.split('.')[:-1])
        base_name = module_name.split('.')[-1]
        parent = load_module_from_name(environ, os.path.dirname(filename),
                                       parent_name, errors)
    else:
        base_name = module_name
    fp = None
    try:
        fp, pathname, stuff = imp.find_module(
            base_name, [os.path.dirname(filename)])
        module = imp.load_module(module_name, fp, pathname, stuff)
    finally:
        if fp is not None:
            fp.close()
    return module

def make_py(parser, environ, filename):
    module = load_module(environ, filename)
    if not module:
        return None
    if hasattr(module, 'application') and module.application:
        return getattr(module.application, 'wsgi_application', module.application)
    base_name = module.__name__.split('.')[-1]
    if hasattr(module, base_name):
        obj = getattr(module, base_name)
        if hasattr(obj, 'wsgi_application'):
            return obj.wsgi_application
        else:
            # @@: Old behavior; should probably be deprecated eventually:
            return getattr(module, base_name)()
    environ['wsgi.errors'].write(
        "Cound not find application or %s in %s\n"
        % (base_name, module))
    return None

URLParser.register_constructor('.py', make_py)

class StaticURLParser(object):
    """
    Like ``URLParser`` but only serves static files.

    ``cache_max_age``:
      integer specifies Cache-Control max_age in seconds
    """
    # @@: Should URLParser subclass from this?

    def __init__(self, directory, root_directory=None,
                 cache_max_age=None):
        self.directory = self.normpath(directory)
        self.root_directory = self.normpath(root_directory or directory)
        self.cache_max_age = cache_max_age

    def normpath(path):
        return os.path.normcase(os.path.abspath(path))
    normpath = staticmethod(normpath)

    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        if not path_info:
            return self.add_slash(environ, start_response)
        if path_info == '/':
            # @@: This should obviously be configurable
            filename = 'index.html'
        else:
            filename = request.path_info_pop(environ)
        full = self.normpath(os.path.join(self.directory, filename))
        if not full.startswith(self.root_directory):
            # Out of bounds
            return self.not_found(environ, start_response)
        if not os.path.exists(full):
            return self.not_found(environ, start_response)
        if os.path.isdir(full):
            # @@: Cache?
            return self.__class__(full, root_directory=self.root_directory,
                                  cache_max_age=self.cache_max_age)(environ,
                                                                   start_response)
        if environ.get('PATH_INFO') and environ.get('PATH_INFO') != '/':
            return self.error_extra_path(environ, start_response)
        if_none_match = environ.get('HTTP_IF_NONE_MATCH')
        if if_none_match:
            mytime = os.stat(full).st_mtime
            if str(mytime) == if_none_match:
                headers = []
                ## FIXME: probably should be
                ## ETAG.update(headers, '"%s"' % mytime)
                ETAG.update(headers, mytime)
                start_response('304 Not Modified', headers)
                return [''] # empty body

        fa = self.make_app(full)
        if self.cache_max_age:
            fa.cache_control(max_age=self.cache_max_age)
        return fa(environ, start_response)

    def make_app(self, filename):
        return fileapp.FileApp(filename)

    def add_slash(self, environ, start_response):
        """
        This happens when you try to get to a directory
        without a trailing /
        """
        url = request.construct_url(environ, with_query_string=False)
        url += '/'
        if environ.get('QUERY_STRING'):
            url += '?' + environ['QUERY_STRING']
        exc = httpexceptions.HTTPMovedPermanently(
            'The resource has moved to %s - you should be redirected '
            'automatically.' % url,
            headers=[('location', url)])
        return exc.wsgi_application(environ, start_response)

    def not_found(self, environ, start_response, debug_message=None):
        exc = httpexceptions.HTTPNotFound(
            'The resource at %s could not be found'
            % request.construct_url(environ),
            comment='SCRIPT_NAME=%r; PATH_INFO=%r; looking in %r; debug: %s'
            % (environ.get('SCRIPT_NAME'), environ.get('PATH_INFO'),
               self.directory, debug_message or '(none)'))
        return exc.wsgi_application(environ, start_response)

    def error_extra_path(self, environ, start_response):
        exc = httpexceptions.HTTPNotFound(
            'The trailing path %r is not allowed' % environ['PATH_INFO'])
        return exc.wsgi_application(environ, start_response)

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.directory)

def make_static(global_conf, document_root, cache_max_age=None):
    """
    Return a WSGI application that serves a directory (configured
    with document_root)

    cache_max_age - integer specifies CACHE_CONTROL max_age in seconds
    """
    if cache_max_age is not None:
        cache_max_age = int(cache_max_age)
    return StaticURLParser(
        document_root, cache_max_age=cache_max_age)

class PkgResourcesParser(StaticURLParser):

    def __init__(self, egg_or_spec, resource_name, manager=None, root_resource=None):
        if pkg_resources is None:
            raise NotImplementedError("This class requires pkg_resources.")
        if isinstance(egg_or_spec, (str, unicode)):
            self.egg = pkg_resources.get_distribution(egg_or_spec)
        else:
            self.egg = egg_or_spec
        self.resource_name = resource_name
        if manager is None:
            manager = pkg_resources.ResourceManager()
        self.manager = manager
        if root_resource is None:
            root_resource = resource_name
        self.root_resource = os.path.normpath(root_resource)

    def __repr__(self):
        return '<%s for %s:%r>' % (
            self.__class__.__name__,
            self.egg.project_name,
            self.resource_name)

    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        if not path_info:
            return self.add_slash(environ, start_response)
        if path_info == '/':
            # @@: This should obviously be configurable
            filename = 'index.html'
        else:
            filename = request.path_info_pop(environ)
        resource = os.path.normcase(os.path.normpath(
                    self.resource_name + '/' + filename))
        if self.root_resource is not None and not resource.startswith(self.root_resource):
            # Out of bounds
            return self.not_found(environ, start_response)
        if not self.egg.has_resource(resource):
            return self.not_found(environ, start_response)
        if self.egg.resource_isdir(resource):
            # @@: Cache?
            child_root = self.root_resource is not None and self.root_resource or \
                self.resource_name
            return self.__class__(self.egg, resource, self.manager,
                                  root_resource=child_root)(environ, start_response)
        if environ.get('PATH_INFO') and environ.get('PATH_INFO') != '/':
            return self.error_extra_path(environ, start_response)

        type, encoding = mimetypes.guess_type(resource)
        if not type:
            type = 'application/octet-stream'
        # @@: I don't know what to do with the encoding.
        try:
            file = self.egg.get_resource_stream(self.manager, resource)
        except (IOError, OSError), e:
            exc = httpexceptions.HTTPForbidden(
                'You are not permitted to view this file (%s)' % e)
            return exc.wsgi_application(environ, start_response)
        start_response('200 OK',
                       [('content-type', type)])
        return fileapp._FileIter(file)

    def not_found(self, environ, start_response, debug_message=None):
        exc = httpexceptions.HTTPNotFound(
            'The resource at %s could not be found'
            % request.construct_url(environ),
            comment='SCRIPT_NAME=%r; PATH_INFO=%r; looking in egg:%s#%r; debug: %s'
            % (environ.get('SCRIPT_NAME'), environ.get('PATH_INFO'),
               self.egg, self.resource_name, debug_message or '(none)'))
        return exc.wsgi_application(environ, start_response)

def make_pkg_resources(global_conf, egg, resource_name=''):
    """
    A static file parser that loads data from an egg using
    ``pkg_resources``.  Takes a configuration value ``egg``, which is
    an egg spec, and a base ``resource_name`` (default empty string)
    which is the path in the egg that this starts at.
    """
    if pkg_resources is None:
        raise NotImplementedError("This function requires pkg_resources.")
    return PkgResourcesParser(egg, resource_name)

def make_url_parser(global_conf, directory, base_python_name,
                    index_names=None, hide_extensions=None,
                    ignore_extensions=None,
                    **constructor_conf):
    """
    Create a URLParser application that looks in ``directory``, which
    should be the directory for the Python package named in
    ``base_python_name``.  ``index_names`` are used when viewing the
    directory (like ``'index'`` for ``'index.html'``).
    ``hide_extensions`` are extensions that are not viewable (like
    ``'.pyc'``) and ``ignore_extensions`` are viewable but only if an
    explicit extension is given.
    """
    if index_names is None:
        index_names = global_conf.get(
            'index_names', ('index', 'Index', 'main', 'Main'))
    index_names = converters.aslist(index_names)

    if hide_extensions is None:
        hide_extensions = global_conf.get(
            'hide_extensions', ('.pyc', 'bak', 'py~'))
    hide_extensions = converters.aslist(hide_extensions)

    if ignore_extensions is None:
        ignore_extensions = global_conf.get(
            'ignore_extensions', ())
    ignore_extensions = converters.aslist(ignore_extensions)
    # There's no real way to set constructors currently...

    return URLParser({}, directory, base_python_name,
                     index_names=index_names,
                     hide_extensions=hide_extensions,
                     ignore_extensions=ignore_extensions,
                     **constructor_conf)
