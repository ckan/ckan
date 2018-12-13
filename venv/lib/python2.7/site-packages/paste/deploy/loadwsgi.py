# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
from __future__ import with_statement
import os
import sys
import re

import pkg_resources

from paste.deploy.compat import ConfigParser, unquote, iteritems, dictkeys
from paste.deploy.util import fix_call, lookup_object

__all__ = ['loadapp', 'loadserver', 'loadfilter', 'appconfig']


############################################################
## Utility functions
############################################################


def import_string(s):
    return pkg_resources.EntryPoint.parse("x=" + s).load(False)


def _aslist(obj):
    """
    Turn object into a list; lists and tuples are left as-is, None
    becomes [], and everything else turns into a one-element list.
    """
    if obj is None:
        return []
    elif isinstance(obj, (list, tuple)):
        return obj
    else:
        return [obj]


def _flatten(lst):
    """
    Flatten a nested list.
    """
    if not isinstance(lst, (list, tuple)):
        return [lst]
    result = []
    for item in lst:
        result.extend(_flatten(item))
    return result


class NicerConfigParser(ConfigParser):

    def __init__(self, filename, *args, **kw):
        ConfigParser.__init__(self, *args, **kw)
        self.filename = filename
        if hasattr(self, '_interpolation'):
            self._interpolation = self.InterpolateWrapper(self._interpolation)

    read_file = getattr(ConfigParser, 'read_file', ConfigParser.readfp)

    def defaults(self):
        """Return the defaults, with their values interpolated (with the
        defaults dict itself)

        Mainly to support defaults using values such as %(here)s
        """
        defaults = ConfigParser.defaults(self).copy()
        for key, val in iteritems(defaults):
            defaults[key] = self.get('DEFAULT', key) or val
        return defaults

    def _interpolate(self, section, option, rawval, vars):
        # Python < 3.2
        try:
            return ConfigParser._interpolate(
                self, section, option, rawval, vars)
        except Exception:
            e = sys.exc_info()[1]
            args = list(e.args)
            args[0] = 'Error in file %s: %s' % (self.filename, e)
            e.args = tuple(args)
            e.message = args[0]
            raise

    class InterpolateWrapper(object):
        # Python >= 3.2
        def __init__(self, original):
            self._original = original

        def __getattr__(self, name):
            return getattr(self._original, name)

        def before_get(self, parser, section, option, value, defaults):
            try:
                return self._original.before_get(parser, section, option,
                                                 value, defaults)
            except Exception:
                e = sys.exc_info()[1]
                args = list(e.args)
                args[0] = 'Error in file %s: %s' % (parser.filename, e)
                e.args = tuple(args)
                e.message = args[0]
                raise


############################################################
## Object types
############################################################


class _ObjectType(object):

    name = None
    egg_protocols = None
    config_prefixes = None

    def __init__(self):
        # Normalize these variables:
        self.egg_protocols = [_aslist(p) for p in _aslist(self.egg_protocols)]
        self.config_prefixes = [_aslist(p) for p in _aslist(self.config_prefixes)]

    def __repr__(self):
        return '<%s protocols=%r prefixes=%r>' % (
            self.name, self.egg_protocols, self.config_prefixes)

    def invoke(self, context):
        assert context.protocol in _flatten(self.egg_protocols)
        return fix_call(context.object,
                        context.global_conf, **context.local_conf)


class _App(_ObjectType):

    name = 'application'
    egg_protocols = ['paste.app_factory', 'paste.composite_factory',
                     'paste.composit_factory']
    config_prefixes = [['app', 'application'], ['composite', 'composit'],
                       'pipeline', 'filter-app']

    def invoke(self, context):
        if context.protocol in ('paste.composit_factory',
                                'paste.composite_factory'):
            return fix_call(context.object,
                            context.loader, context.global_conf,
                            **context.local_conf)
        elif context.protocol == 'paste.app_factory':
            return fix_call(context.object, context.global_conf, **context.local_conf)
        else:
            assert 0, "Protocol %r unknown" % context.protocol

APP = _App()


class _Filter(_ObjectType):
    name = 'filter'
    egg_protocols = [['paste.filter_factory', 'paste.filter_app_factory']]
    config_prefixes = ['filter']

    def invoke(self, context):
        if context.protocol == 'paste.filter_factory':
            return fix_call(context.object,
                            context.global_conf, **context.local_conf)
        elif context.protocol == 'paste.filter_app_factory':
            def filter_wrapper(wsgi_app):
                # This should be an object, so it has a nicer __repr__
                return fix_call(context.object,
                                wsgi_app, context.global_conf,
                                **context.local_conf)
            return filter_wrapper
        else:
            assert 0, "Protocol %r unknown" % context.protocol

FILTER = _Filter()


class _Server(_ObjectType):
    name = 'server'
    egg_protocols = [['paste.server_factory', 'paste.server_runner']]
    config_prefixes = ['server']

    def invoke(self, context):
        if context.protocol == 'paste.server_factory':
            return fix_call(context.object,
                            context.global_conf, **context.local_conf)
        elif context.protocol == 'paste.server_runner':
            def server_wrapper(wsgi_app):
                # This should be an object, so it has a nicer __repr__
                return fix_call(context.object,
                                wsgi_app, context.global_conf,
                                **context.local_conf)
            return server_wrapper
        else:
            assert 0, "Protocol %r unknown" % context.protocol

SERVER = _Server()


# Virtual type: (@@: There's clearly something crufty here;
# this probably could be more elegant)
class _PipeLine(_ObjectType):
    name = 'pipeline'

    def invoke(self, context):
        app = context.app_context.create()
        filters = [c.create() for c in context.filter_contexts]
        filters.reverse()
        for filter in filters:
            app = filter(app)
        return app

PIPELINE = _PipeLine()


class _FilterApp(_ObjectType):
    name = 'filter_app'

    def invoke(self, context):
        next_app = context.next_context.create()
        filter = context.filter_context.create()
        return filter(next_app)

FILTER_APP = _FilterApp()


class _FilterWith(_App):
    name = 'filtered_with'

    def invoke(self, context):
        filter = context.filter_context.create()
        filtered = context.next_context.create()
        if context.next_context.object_type is APP:
            return filter(filtered)
        else:
            # filtering a filter
            def composed(app):
                return filter(filtered(app))
            return composed

FILTER_WITH = _FilterWith()


############################################################
## Loaders
############################################################


def loadapp(uri, name=None, **kw):
    return loadobj(APP, uri, name=name, **kw)


def loadfilter(uri, name=None, **kw):
    return loadobj(FILTER, uri, name=name, **kw)


def loadserver(uri, name=None, **kw):
    return loadobj(SERVER, uri, name=name, **kw)


def appconfig(uri, name=None, relative_to=None, global_conf=None):
    context = loadcontext(APP, uri, name=name,
                          relative_to=relative_to,
                          global_conf=global_conf)
    return context.config()

_loaders = {}


def loadobj(object_type, uri, name=None, relative_to=None,
            global_conf=None):
    context = loadcontext(
        object_type, uri, name=name, relative_to=relative_to,
        global_conf=global_conf)
    return context.create()


def loadcontext(object_type, uri, name=None, relative_to=None,
                global_conf=None):
    if '#' in uri:
        if name is None:
            uri, name = uri.split('#', 1)
        else:
            # @@: Ignore fragment or error?
            uri = uri.split('#', 1)[0]
    if name is None:
        name = 'main'
    if ':' not in uri:
        raise LookupError("URI has no scheme: %r" % uri)
    scheme, path = uri.split(':', 1)
    scheme = scheme.lower()
    if scheme not in _loaders:
        raise LookupError(
            "URI scheme not known: %r (from %s)"
            % (scheme, ', '.join(_loaders.keys())))
    return _loaders[scheme](
        object_type,
        uri, path, name=name, relative_to=relative_to,
        global_conf=global_conf)


def _loadconfig(object_type, uri, path, name, relative_to,
                global_conf):
    isabs = os.path.isabs(path)
    # De-Windowsify the paths:
    path = path.replace('\\', '/')
    if not isabs:
        if not relative_to:
            raise ValueError(
                "Cannot resolve relative uri %r; no relative_to keyword "
                "argument given" % uri)
        relative_to = relative_to.replace('\\', '/')
        if relative_to.endswith('/'):
            path = relative_to + path
        else:
            path = relative_to + '/' + path
    if path.startswith('///'):
        path = path[2:]
    path = unquote(path)
    loader = ConfigLoader(path)
    if global_conf:
        loader.update_defaults(global_conf, overwrite=False)
    return loader.get_context(object_type, name, global_conf)

_loaders['config'] = _loadconfig


def _loadegg(object_type, uri, spec, name, relative_to,
             global_conf):
    loader = EggLoader(spec)
    return loader.get_context(object_type, name, global_conf)

_loaders['egg'] = _loadegg


def _loadfunc(object_type, uri, spec, name, relative_to,
             global_conf):

    loader = FuncLoader(spec)
    return loader.get_context(object_type, name, global_conf)

_loaders['call'] = _loadfunc

############################################################
## Loaders
############################################################


class _Loader(object):

    def get_app(self, name=None, global_conf=None):
        return self.app_context(
            name=name, global_conf=global_conf).create()

    def get_filter(self, name=None, global_conf=None):
        return self.filter_context(
            name=name, global_conf=global_conf).create()

    def get_server(self, name=None, global_conf=None):
        return self.server_context(
            name=name, global_conf=global_conf).create()

    def app_context(self, name=None, global_conf=None):
        return self.get_context(
            APP, name=name, global_conf=global_conf)

    def filter_context(self, name=None, global_conf=None):
        return self.get_context(
            FILTER, name=name, global_conf=global_conf)

    def server_context(self, name=None, global_conf=None):
        return self.get_context(
            SERVER, name=name, global_conf=global_conf)

    _absolute_re = re.compile(r'^[a-zA-Z]+:')

    def absolute_name(self, name):
        """
        Returns true if the name includes a scheme
        """
        if name is None:
            return False
        return self._absolute_re.search(name)


class ConfigLoader(_Loader):

    def __init__(self, filename):
        self.filename = filename = filename.strip()
        defaults = {
            'here': os.path.dirname(os.path.abspath(filename)),
            '__file__': os.path.abspath(filename)
            }
        self.parser = NicerConfigParser(filename, defaults=defaults)
        self.parser.optionxform = str  # Don't lower-case keys
        with open(filename) as f:
            self.parser.read_file(f)

    def update_defaults(self, new_defaults, overwrite=True):
        for key, value in iteritems(new_defaults):
            if not overwrite and key in self.parser._defaults:
                continue
            self.parser._defaults[key] = value

    def get_context(self, object_type, name=None, global_conf=None):
        if self.absolute_name(name):
            return loadcontext(object_type, name,
                               relative_to=os.path.dirname(self.filename),
                               global_conf=global_conf)
        section = self.find_config_section(
            object_type, name=name)
        if global_conf is None:
            global_conf = {}
        else:
            global_conf = global_conf.copy()
        defaults = self.parser.defaults()
        global_conf.update(defaults)
        local_conf = {}
        global_additions = {}
        get_from_globals = {}
        for option in self.parser.options(section):
            if option.startswith('set '):
                name = option[4:].strip()
                global_additions[name] = global_conf[name] = (
                    self.parser.get(section, option))
            elif option.startswith('get '):
                name = option[4:].strip()
                get_from_globals[name] = self.parser.get(section, option)
            else:
                if option in defaults:
                    # @@: It's a global option (?), so skip it
                    continue
                local_conf[option] = self.parser.get(section, option)
        for local_var, glob_var in get_from_globals.items():
            local_conf[local_var] = global_conf[glob_var]
        if object_type in (APP, FILTER) and 'filter-with' in local_conf:
            filter_with = local_conf.pop('filter-with')
        else:
            filter_with = None
        if 'require' in local_conf:
            for spec in local_conf['require'].split():
                pkg_resources.require(spec)
            del local_conf['require']
        if section.startswith('filter-app:'):
            context = self._filter_app_context(
                object_type, section, name=name,
                global_conf=global_conf, local_conf=local_conf,
                global_additions=global_additions)
        elif section.startswith('pipeline:'):
            context = self._pipeline_app_context(
                object_type, section, name=name,
                global_conf=global_conf, local_conf=local_conf,
                global_additions=global_additions)
        elif 'use' in local_conf:
            context = self._context_from_use(
                object_type, local_conf, global_conf, global_additions,
                section)
        else:
            context = self._context_from_explicit(
                object_type, local_conf, global_conf, global_additions,
                section)
        if filter_with is not None:
            filter_with_context = LoaderContext(
                obj=None,
                object_type=FILTER_WITH,
                protocol=None,
                global_conf=global_conf, local_conf=local_conf,
                loader=self)
            filter_with_context.filter_context = self.filter_context(
                name=filter_with, global_conf=global_conf)
            filter_with_context.next_context = context
            return filter_with_context
        return context

    def _context_from_use(self, object_type, local_conf, global_conf,
                          global_additions, section):
        use = local_conf.pop('use')
        context = self.get_context(
            object_type, name=use, global_conf=global_conf)
        context.global_conf.update(global_additions)
        context.local_conf.update(local_conf)
        if '__file__' in global_conf:
            # use sections shouldn't overwrite the original __file__
            context.global_conf['__file__'] = global_conf['__file__']
        # @@: Should loader be overwritten?
        context.loader = self

        if context.protocol is None:
            # Determine protocol from section type
            section_protocol = section.split(':', 1)[0]
            if section_protocol in ('application', 'app'):
                context.protocol = 'paste.app_factory'
            elif section_protocol in ('composit', 'composite'):
                context.protocol = 'paste.composit_factory'
            else:
                # This will work with 'server' and 'filter', otherwise it
                # could fail but there is an error message already for
                # bad protocols
                context.protocol = 'paste.%s_factory' % section_protocol

        return context

    def _context_from_explicit(self, object_type, local_conf, global_conf,
                               global_addition, section):
        possible = []
        for protocol_options in object_type.egg_protocols:
            for protocol in protocol_options:
                if protocol in local_conf:
                    possible.append((protocol, local_conf[protocol]))
                    break
        if len(possible) > 1:
            raise LookupError(
                "Multiple protocols given in section %r: %s"
                % (section, possible))
        if not possible:
            raise LookupError(
                "No loader given in section %r" % section)
        found_protocol, found_expr = possible[0]
        del local_conf[found_protocol]
        value = import_string(found_expr)
        context = LoaderContext(
            value, object_type, found_protocol,
            global_conf, local_conf, self)
        return context

    def _filter_app_context(self, object_type, section, name,
                            global_conf, local_conf, global_additions):
        if 'next' not in local_conf:
            raise LookupError(
                "The [%s] section in %s is missing a 'next' setting"
                % (section, self.filename))
        next_name = local_conf.pop('next')
        context = LoaderContext(None, FILTER_APP, None, global_conf,
                                local_conf, self)
        context.next_context = self.get_context(
            APP, next_name, global_conf)
        if 'use' in local_conf:
            context.filter_context = self._context_from_use(
                FILTER, local_conf, global_conf, global_additions,
                section)
        else:
            context.filter_context = self._context_from_explicit(
                FILTER, local_conf, global_conf, global_additions,
                section)
        return context

    def _pipeline_app_context(self, object_type, section, name,
                              global_conf, local_conf, global_additions):
        if 'pipeline' not in local_conf:
            raise LookupError(
                "The [%s] section in %s is missing a 'pipeline' setting"
                % (section, self.filename))
        pipeline = local_conf.pop('pipeline').split()
        if local_conf:
            raise LookupError(
                "The [%s] pipeline section in %s has extra "
                "(disallowed) settings: %s"
                % (', '.join(local_conf.keys())))
        context = LoaderContext(None, PIPELINE, None, global_conf,
                                local_conf, self)
        context.app_context = self.get_context(
            APP, pipeline[-1], global_conf)
        context.filter_contexts = [
            self.get_context(FILTER, name, global_conf)
            for name in pipeline[:-1]]
        return context

    def find_config_section(self, object_type, name=None):
        """
        Return the section name with the given name prefix (following the
        same pattern as ``protocol_desc`` in ``config``.  It must have the
        given name, or for ``'main'`` an empty name is allowed.  The
        prefix must be followed by a ``:``.

        Case is *not* ignored.
        """
        possible = []
        for name_options in object_type.config_prefixes:
            for name_prefix in name_options:
                found = self._find_sections(
                    self.parser.sections(), name_prefix, name)
                if found:
                    possible.extend(found)
                    break
        if not possible:
            raise LookupError(
                "No section %r (prefixed by %s) found in config %s"
                % (name,
                   ' or '.join(map(repr, _flatten(object_type.config_prefixes))),
                   self.filename))
        if len(possible) > 1:
            raise LookupError(
                "Ambiguous section names %r for section %r (prefixed by %s) "
                "found in config %s"
                % (possible, name,
                   ' or '.join(map(repr, _flatten(object_type.config_prefixes))),
                   self.filename))
        return possible[0]

    def _find_sections(self, sections, name_prefix, name):
        found = []
        if name is None:
            if name_prefix in sections:
                found.append(name_prefix)
            name = 'main'
        for section in sections:
            if section.startswith(name_prefix + ':'):
                if section[len(name_prefix) + 1:].strip() == name:
                    found.append(section)
        return found


class EggLoader(_Loader):

    def __init__(self, spec):
        self.spec = spec

    def get_context(self, object_type, name=None, global_conf=None):
        if self.absolute_name(name):
            return loadcontext(object_type, name,
                               global_conf=global_conf)
        entry_point, protocol, ep_name = self.find_egg_entry_point(
            object_type, name=name)
        return LoaderContext(
            entry_point,
            object_type,
            protocol,
            global_conf or {}, {},
            self,
            distribution=pkg_resources.get_distribution(self.spec),
            entry_point_name=ep_name)

    def find_egg_entry_point(self, object_type, name=None):
        """
        Returns the (entry_point, protocol) for the with the given
        ``name``.
        """
        if name is None:
            name = 'main'
        possible = []
        for protocol_options in object_type.egg_protocols:
            for protocol in protocol_options:
                pkg_resources.require(self.spec)
                entry = pkg_resources.get_entry_info(
                    self.spec,
                    protocol,
                    name)
                if entry is not None:
                    possible.append((entry.load(), protocol, entry.name))
                    break
        if not possible:
            # Better exception
            dist = pkg_resources.get_distribution(self.spec)
            raise LookupError(
                "Entry point %r not found in egg %r (dir: %s; protocols: %s; "
                "entry_points: %s)"
                % (name, self.spec,
                   dist.location,
                   ', '.join(_flatten(object_type.egg_protocols)),
                   ', '.join(_flatten([
                dictkeys(pkg_resources.get_entry_info(self.spec, prot, name) or {})
                for prot in protocol_options] or '(no entry points)'))))
        if len(possible) > 1:
            raise LookupError(
                "Ambiguous entry points for %r in egg %r (protocols: %s)"
                % (name, self.spec, ', '.join(_flatten(protocol_options))))
        return possible[0]


class FuncLoader(_Loader):
    """ Loader that supports specifying functions inside modules, without
    using eggs at all. Configuration should be in the format:
        use = call:my.module.path:function_name
        
    Dot notation is supported in both the module and function name, e.g.:
        use = call:my.module.path:object.method
    """
    def __init__(self, spec):
        self.spec = spec
        if not ':' in spec:
            raise LookupError("Configuration not in format module:function")

    def get_context(self, object_type, name=None, global_conf=None):
        obj = lookup_object(self.spec)
        return LoaderContext(
            obj,
            object_type,
            None, # determine protocol from section type
            global_conf or {},
            {},
            self,
            )


class LoaderContext(object):

    def __init__(self, obj, object_type, protocol,
                 global_conf, local_conf, loader,
                 distribution=None, entry_point_name=None):
        self.object = obj
        self.object_type = object_type
        self.protocol = protocol
        #assert protocol in _flatten(object_type.egg_protocols), (
        #    "Bad protocol %r; should be one of %s"
        #    % (protocol, ', '.join(map(repr, _flatten(object_type.egg_protocols)))))
        self.global_conf = global_conf
        self.local_conf = local_conf
        self.loader = loader
        self.distribution = distribution
        self.entry_point_name = entry_point_name

    def create(self):
        return self.object_type.invoke(self)

    def config(self):
        conf = AttrDict(self.global_conf)
        conf.update(self.local_conf)
        conf.local_conf = self.local_conf
        conf.global_conf = self.global_conf
        conf.context = self
        return conf


class AttrDict(dict):
    """
    A dictionary that can be assigned to.
    """
    pass
