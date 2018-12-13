"""Legacy (older versions of Pylons) functionality and warnings"""
import sys
import types
import warnings

from paste.registry import StackedObjectProxy

import pylons
import pylons.decorators
from pylons.controllers.util import Response as PylonsResponse
from pylons.util import deprecated, func_move

__all__ = ['load_h']

config_attr_moved = (
    "The attribute 'config.%s' has moved to the pylons.config dictionary: "
    "Please access it via pylons.config['%s']")

config_load_environment = (
"The pylons.config.Config object is deprecated. Please load the environment "
"configuration via the pylons.config object in config/environment.py instead, "
".e.g:"
"""

    from pylons import config

And in in the load_environment function:

    config['routes.map'] = map

    # The template options
    tmpl_options = config['buffet.template_options']

    # CONFIGURATION OPTIONS HERE (note: all config options will override any
    # Pylons config options)

See the default config/environment.py created via the "paster create -t pylons"
command for a full example.
""")

default_charset_warning = (
"The 'default_charset' keyword argument to the %(klass)s constructor is "
"deprecated. Please specify the charset in the response_options dictionary "
"in your config/environment.py file instead, .e.g."
"""

    from pylons import config

Add the following lines to the end of the load_environment function:

    config['pylons.response_options']['charset'] = '%(charset)s'
""")

error_template_warning = (
"""The 'error_template' errorware argument for customizing EvalException is \
deprecated, please remove it. To customize EvalException's HTML, setup your \
own EvalException and ErrorMiddlewares instead of using ErrorHandler."""
)

log_warning = (
'The log function is deprecated. Use the logging module instead')

prefix_warning = (
"The [app:main] 'prefix' configuration option has been deprecated, please use "
"paste.deploy.config.PrefixMiddleware instead. To enable PrefixMiddleware in "
"""the config file, add the following line to the [app:main] section:

    filter-with = app-prefix

and the following lines to the end of the config file:

    [filter:app-prefix]
    use = egg:PasteDeploy#prefix
    prefix = %s
""")

pylons_database_warning = (
"pylons.database is deprecated, and will be removed from a future version of "
"Pylons. SQLAlchemy 0.3.x users are recommended to migrate to SAContext "
"(http://cheeseshop.python.org/pypi/SAContext) for similar functionality")

pylons_h_warning = (
"pylons.h is deprecated: use your project's lib.helpers module directly "
"""instead. Your lib/helpers.py may require the following additional imports:

    from pylons.helpers import log
    from pylons.i18n import get_lang, set_lang

Use the following in your project's lib/base.py file (and any other module that
uses h):

    import MYPROJ.lib.helpers as h

(where MYPROJ is the name of your project) instead of:

    from pylons import h
""")

render_response_warning = (
"render_response is deprecated, please return the response content directly "
"(via the render function) instead")

root_path = (
"paths['root_path'] has been moved to paths['root'], please update your "
"configuration")

def load_h(package_name):
    """
    This is a legacy test for pre-0.9.3 projects to continue using the old
    style Helper imports. The proper style is to pass the helpers module ref
    to the PylonsApp during initialization.
    """
    __import__(package_name + '.lib.base')
    their_h = getattr(sys.modules[package_name + '.lib.base'], 'h', None)
    if isinstance(their_h, types.ModuleType):
        # lib.base.h is a module (and thus not pylons.h) -- assume lib.base
        # uses new style (self contained) helpers via:
        # import ${package}.lib.helpers as h
        return their_h

    # Assume lib.base.h is a StackedObjectProxy -- lib.base is using pre 0.9.2
    # style helpers via:
    # from pylons import h
    helpers_name = package_name + '.lib.helpers'
    __import__(helpers_name)
    return sys.modules[helpers_name]

jsonify = deprecated(pylons.decorators.jsonify,
                     func_move('pylons.jsonify',
                               moved_to='pylons.decorators.jsonify'))

class DeprecatedStackedObjectProxy(StackedObjectProxy):
    def _current_obj(*args, **kwargs):
        warnings.warn(pylons_h_warning, DeprecationWarning, 3)
        return StackedObjectProxy._current_obj(*args, **kwargs)
h = DeprecatedStackedObjectProxy(name="h")

response_warning = (
"Returning a Response object from a controller is deprecated, and support for "
"it will be removed in a future version of Pylons. Please return the response "
"content directly and or use pylons.response instead")
class Response(PylonsResponse):
    def __init__(self, *args, **kwargs):
        warnings.warn(response_warning, DeprecationWarning, 2)
        PylonsResponse.__init__(self, *args, **kwargs)
