"""Paste Template and Pylons utility functions

PylonsTemplate is a Paste Template sub-class that configures the source
directory and default plug-ins for a new Pylons project. The minimal
template a more minimal template with less additional directories and
layout.

The functions used in this module are to assist Pylons in creating new
projects, and handling deprecation warnings for moved Pylons functions.

"""
import logging
import sys
import warnings

import pkg_resources
from paste.deploy.converters import asbool
from paste.script.appinstall import Installer
from paste.script.templates import Template, var
from tempita import paste_script_template_renderer

import pylons
import pylons.configuration
import pylons.i18n

__all__ = ['AttribSafeContextObj', 'ContextObj', 'PylonsContext',
           'class_name_from_module_name', 'call_wsgi_application']

pylons_log = logging.getLogger(__name__)

def func_move(name, moved_to='pylons.i18n'):
    return ("The %s function has moved to %s, please update your import "
            "statements to reflect the move" % (name, moved_to))


def deprecated(func, message):
    def deprecated_method(*args, **kargs):
        warnings.warn(message, DeprecationWarning, 2)
        return func(*args, **kargs)
    try:
        deprecated_method.__name__ = func.__name__
    except TypeError: # Python < 2.4
        pass
    deprecated_method.__doc__ = "%s\n\n%s" % (message, func.__doc__)
    return deprecated_method


get_lang = deprecated(pylons.i18n.get_lang, func_move('get_lang'))
set_lang = deprecated(pylons.i18n.set_lang, func_move('set_lang'))
_ = deprecated(pylons.i18n._, func_move('_'))

# Avoid circular import and a double warning
def log(*args, **kwargs):
    """Deprecated: Use the logging module instead.

    Log a message to the output log.
    """
    import pylons.helpers
    return pylons.helpers.log(*args, **kwargs)

def get_prefix(environ, warn=True):
    """Deprecated: Use environ.get('SCRIPT_NAME', '') instead"""
    if warn:
        warnings.warn("The get_prefix function is deprecated, please use "
                      "environ.get('SCRIPT_NAME', '') instead",
                      DeprecationWarning, 2)
    prefix = pylons.config.get('prefix', '')
    if not prefix:
        if environ.get('SCRIPT_NAME', '') != '':
            prefix = environ['SCRIPT_NAME']
    return prefix


def call_wsgi_application(application, environ, catch_exc_info=False):
    """
    Call the given WSGI application, returning ``(status_string,
    headerlist, app_iter)``

    Be sure to call ``app_iter.close()`` if it's there.

    If catch_exc_info is true, then returns ``(status_string,
    headerlist, app_iter, exc_info)``, where the fourth item may
    be None, but won't be if there was an exception.  If you don't
    do this and there was an exception, the exception will be
    raised directly.
    """
    captured = []
    output = []
    def start_response(status, headers, exc_info=None):
        if exc_info is not None and not catch_exc_info:
            raise exc_info[0], exc_info[1], exc_info[2]
        captured[:] = [status, headers, exc_info]
        return output.append
    app_iter = application(environ, start_response)
    if not captured or output:
        try:
            output.extend(app_iter)
        finally:
            if hasattr(app_iter, 'close'):
                app_iter.close()
        app_iter = output
    if catch_exc_info:
        return (captured[0], captured[1], app_iter, captured[2])
    else:
        return (captured[0], captured[1], app_iter)


def class_name_from_module_name(module_name):
    """Takes a module name and returns the name of the class it
    defines.

    If the module name contains dashes, they are replaced with
    underscores.

    Example::

        >>> class_name_from_module_name('with-dashes')
        'WithDashes'
        >>> class_name_from_module_name('with_underscores')
        'WithUnderscores'
        >>> class_name_from_module_name('oneword')
        'Oneword'

    """
    words = module_name.replace('-', '_').split('_')
    return ''.join([w.title() for w in words])


class PylonsContext(object):
    """Pylons context object
    
    All the Pylons Stacked Object Proxies are also stored here, for use
    in generators and async based operation where the globals can't be
    used.
    
    This object is attached in
    :class:`~pylons.controllers.core.WSGIController` instances as
    :attr:`~WSGIController._py_object`. For example::

        class MyController(WSGIController):
            def index(self):
                pyobj = self._py_object
                return "Environ is %s" % pyobj.request.environ
    
    """
    pass


class ContextObj(object):
    """The :term:`tmpl_context` object, with strict attribute access
    (raises an Exception when the attribute does not exist)"""
    def __repr__(self):
        attrs = [(name, value)
                 for name, value in self.__dict__.items()
                 if not name.startswith('_')]
        attrs.sort()
        parts = []
        for name, value in attrs:
            value_repr = repr(value)
            if len(value_repr) > 70:
                value_repr = value_repr[:60] + '...' + value_repr[-5:]
            parts.append(' %s=%s' % (name, value_repr))
        return '<%s.%s at %s%s>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            hex(id(self)),
            ','.join(parts))


class AttribSafeContextObj(ContextObj):
    """The :term:`tmpl_context` object, with lax attribute access (
    returns '' when the attribute does not exist)"""
    def __getattr__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            pylons_log.debug("No attribute called %s found on c object, "
                             "returning empty string", name)
            return ''


class PylonsTemplate(Template):
    _template_dir = ('pylons', 'templates/default_project')
    template_renderer = staticmethod(paste_script_template_renderer)
    summary = 'Pylons application template'
    egg_plugins = ['PasteScript', 'Pylons']
    vars = [
        var('template_engine', 'mako/genshi/jinja2/etc: Template language', 
            default='mako'),
        var('sqlalchemy', 'True/False: Include SQLAlchemy 0.5 configuration',
            default=False),
    ]
    ensure_names = ['description', 'author', 'author_email', 'url']
    
    def pre(self, command, output_dir, vars):
        """Called before template is applied."""
        package_logger = vars['package']
        if package_logger == 'root':
            # Rename the app logger in the rare case a project is named 'root'
            package_logger = 'app'
        vars['package_logger'] = package_logger

        template_engine = \
            vars.setdefault('template_engine',
                            pylons.configuration.default_template_engine)

        if template_engine == 'mako':
            # Support a Babel extractor default for Mako
            vars['babel_templates_extractor'] = \
                ("('templates/**.mako', 'mako', {'input_encoding': 'utf-8'})"
                 ",\n%s#%s" % (' ' * 4, ' ' * 8))
        else:
            vars['babel_templates_extractor'] = ''

        # Ensure these exist in the namespace
        for name in self.ensure_names:
            vars.setdefault(name, '')

        vars['version'] = vars.get('version', '0.1')
        vars['zip_safe'] = asbool(vars.get('zip_safe', 'false'))
        vars['sqlalchemy'] = asbool(vars.get('sqlalchemy', 'false'))


class MinimalPylonsTemplate(PylonsTemplate):
    _template_dir = ('pylons', 'templates/minimal_project')
    summary = 'Pylons minimal application template'
    vars = [
        var('template_engine', 'mako/genshi/jinja2/etc: Template language', 
            default='mako'),
    ]


class PylonsInstaller(Installer):
    use_cheetah = False
    config_file = 'config/deployment.ini_tmpl'

    def config_content(self, command, vars):
        """
        Called by ``self.write_config``, this returns the text content
        for the config file, given the provided variables.
        """
        modules = [line.strip()
                    for line in self.dist.get_metadata_lines('top_level.txt')
                    if line.strip() and not line.strip().startswith('#')]
        if not modules:
            print >> sys.stderr, 'No modules are listed in top_level.txt'
            print >> sys.stderr, \
                'Try running python setup.py egg_info to regenerate that file'
        for module in modules:
            if pkg_resources.resource_exists(module, self.config_file):
                return self.template_renderer(
                    pkg_resources.resource_string(module, self.config_file),
                    vars, filename=self.config_file)
        # Legacy support for the old location in egg-info
        return super(PylonsInstaller, self).config_content(command, vars)
