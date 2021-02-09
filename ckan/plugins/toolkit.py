# encoding: utf-8

import sys


class _Toolkit(object):
    '''This class is intended to make functions/objects consistently
    available to plugins, whilst giving core CKAN developers the ability move
    code around or change underlying frameworks etc. This object allows
    us to avoid circular imports while making functions/objects
    available to plugins.

    It should not be used internally within ckan - only by extensions.

    Functions/objects should only be removed after reasonable
    deprecation notice has been given.'''

    # contents should describe the available functions/objects. We check
    # that this list matches the actual availables in the initialisation
    contents = [
        # Global CKAN configuration object
        'config',
        # i18n translation
        '_',
        # i18n translation (plural form)
        'ungettext',
        # template context (deprecated)
        'c',
        # Flask global object
        'g',
        # template helpers
        'h',
        # http request object
        'request',
        # template render function
        'render',
        # snippet render function
        'render_snippet',
        # converts a string to a boolean
        'asbool',
        # converts a string to an integer
        'asint',
        # converts a string to a list
        'aslist',
        # stop tags in a string being escaped
        'literal',
        # get logic action function
        'get_action',
        # get flask/pylons endpoint fragments
        'get_endpoint',
        # decorator for chained action
        'chained_action',
        # get navl schema converter
        'get_converter',
        # get navl schema validator
        'get_validator',
        # check logic function authorisation
        'check_access',
        # decorator for chained authentication functions
        'chained_auth_function',
        # implements validate method with navl schema
        'navl_validate',
        # placeholder for missing values for validation
        'missing',
        # action not found exception (ckan.logic.NotFound)
        'ObjectNotFound',
        # action not authorized exception
        'NotAuthorized',
        # validator not found exception
        'UnknownValidator',
        # model update validation error
        'ValidationError',
        # validation exception to stop further validators from being called
        'StopOnError',
        # validation invalid exception
        'Invalid',
        # old class for providing CLI interfaces
        'CkanCommand',
        # function for initializing CLI interfaces
        'load_config',
        # function to promt the exception in CLI command
        'error_shout',
        # base class for IDatasetForm plugins
        'DefaultDatasetForm',
        # base class for IGroupForm plugins
        'DefaultGroupForm',
        # base class for IGroupForm plugins for orgs
        'DefaultOrganizationForm',
        # response object for cookies etc
        'response',
        # Allow controllers to be created
        'BaseController',
        # abort actions
        'abort',
        # allow redirections
        'redirect_to',
        # create urls
        'url_for',
        # helpful for actions
        'get_or_bust',
        # actions can be accessed via api
        'side_effect_free',
        # allow auth functions to be checked for sysadmins
        'auth_sysadmins_check',
        # allow anonymous access to an auth function
        'auth_allow_anonymous_access',
        # disallow anonymous access to an auth function
        'auth_disallow_anonymous_access',
        # Helper not found error.
        'HelperError',
        # Enqueue background job
        'enqueue_job',
        # Email a recipient
        'mail_recipient',
        # Email a user
        'mail_user',

        # Fully defined in this file ##
        'add_template_directory',
        'add_resource',
        'add_public_directory',
        'add_ckan_admin_tab',
        'requires_ckan_version',
        'check_ckan_version',
        'CkanVersionException',
    ]

    def __init__(self):
        self._toolkit = {}

        # For some members in the the toolkit (e.g. that are exported from
        # third-party libraries) we override their docstrings by putting our
        # own docstrings into this dict. The Sphinx plugin that documents this
        # plugins toolkit will use these docstring overrides instead of the
        # object's actual docstring, when present.
        self.docstring_overrides = {}

    def _initialize(self):
        ''' get the required functions/objects, store them for later
        access and check that they match the contents dict. '''
        import six
        import ckan
        import ckan.logic as logic

        import ckan.lib.base as base
        import ckan.logic.validators as logic_validators
        import ckan.lib.navl.dictization_functions as dictization_functions
        import ckan.lib.helpers as h
        import ckan.cli as cli
        import ckan.lib.plugins as lib_plugins
        import ckan.common as common
        from ckan.exceptions import (
            CkanVersionException,
            HelperError
        )
        from ckan.lib.jobs import enqueue as enqueue_job
        from ckan.lib import mailer

        import ckan.common as converters
        if six.PY2:
            import ckan.lib.cli as old_cli
            import pylons

        # Allow class access to these modules
        self.__class__.ckan = ckan
        self.__class__.base = base

        t = self._toolkit

        # imported functions
        t['config'] = common.config
        self.docstring_overrides['config'] = '''The CKAN configuration object.

It stores the configuration values defined in the :ref:`config_file`, eg::

    title = toolkit.config.get("ckan.site_title")

'''
        t['_'] = common._
        self.docstring_overrides['_'] = '''Translates a string to the
current locale.

The ``_()`` function is a reference to the ``ugettext()`` function.
Everywhere in your code where you want strings to be internationalized
(made available for translation into different languages), wrap them in the
``_()`` function, eg.::

    msg = toolkit._("Hello")

Returns the localized unicode string.
'''
        t['ungettext'] = common.ungettext
        self.docstring_overrides['ungettext'] = '''Translates a string with
plural forms to the current locale.

Mark a string for translation that has pural forms in the format
``ungettext(singular, plural, n)``. Returns the localized unicode string of
the pluralized value.

Mark a string to be localized as follows::

    msg = toolkit.ungettext("Mouse", "Mice", len(mouses))

'''
        t['c'] = common.c
        self.docstring_overrides['c'] = '''The Pylons template context object.

[Deprecated]: Use ``toolkit.g`` instead.

This object is used to pass request-specific information to different parts of
the code in a thread-safe way (so that variables from different requests being
executed at the same time don't get confused with each other).

Any attributes assigned to :py:attr:`~ckan.plugins.toolkit.c` are
available throughout the template and application code, and are local to the
current request.

'''

        t['g'] = common.g
        self.docstring_overrides['g'] = '''The Flask global object.

This object is used to pass request-specific information to different parts of
the code in a thread-safe way (so that variables from different requests being
executed at the same time don't get confused with each other).

Any attributes assigned to :py:attr:`~ckan.plugins.toolkit.g` are
available throughout the template and application code, and are local to the
current request (Note that ``g`` won't be available on templates rendered
by old endpoints served by Pylons).

It is a bad pattern to pass variables to the templates using the ``g`` object.
Pass them explicitly from the view functions as ``extra_vars``, eg::

    return toolkit.render(
        'myext/package/read.html',
        extra_vars={
            u'some_var': some_value,
            u'some_other_var': some_other_value,
        }
    )

'''

        t['h'] = h.helper_functions
        t['request'] = common.request
        self.docstring_overrides['request'] = '''The Pylons request object.

A new request object is created for each HTTP request. It has methods and
attributes for getting things like the request headers, query-string variables,
request body variables, cookies, the request URL, etc.

'''
        t['render'] = base.render
        t['abort'] = base.abort
        t['asbool'] = converters.asbool
        self.docstring_overrides['asbool'] = '''Convert a string (e.g. 1,
true, True) from the config file into a boolean.

For example: ``if toolkit.asbool(config.get('ckan.legacy_templates', False)):``

'''
        t['asint'] = converters.asint
        self.docstring_overrides['asint'] = '''Convert a string from the config
file into an int.

For example: ``bar = toolkit.asint(config.get('ckan.foo.bar', 0))``

'''
        t['aslist'] = converters.aslist
        self.docstring_overrides['aslist'] = '''Convert a space-separated
string from the config file into a list.

For example: ``bar = toolkit.aslist(config.get('ckan.foo.bar', []))``

'''
        t['literal'] = h.literal
        t['get_action'] = logic.get_action
        t['chained_action'] = logic.chained_action
        t['get_converter'] = logic.get_validator  # For backwards compatibility
        t['get_validator'] = logic.get_validator
        t['check_access'] = logic.check_access
        t['chained_auth_function'] = logic.chained_auth_function
        t['navl_validate'] = dictization_functions.validate
        t['missing'] = dictization_functions.missing
        t['ObjectNotFound'] = logic.NotFound  # Name change intentional
        t['NotAuthorized'] = logic.NotAuthorized
        t['ValidationError'] = logic.ValidationError
        t['StopOnError'] = dictization_functions.StopOnError
        t['UnknownValidator'] = logic.UnknownValidator
        t['Invalid'] = logic_validators.Invalid
        t['DefaultDatasetForm'] = lib_plugins.DefaultDatasetForm
        t['DefaultGroupForm'] = lib_plugins.DefaultGroupForm
        t['DefaultOrganizationForm'] = lib_plugins.DefaultOrganizationForm

        t['error_shout'] = cli.error_shout

        t['redirect_to'] = h.redirect_to
        t['url_for'] = h.url_for
        t['get_or_bust'] = logic.get_or_bust
        t['side_effect_free'] = logic.side_effect_free
        t['auth_sysadmins_check'] = logic.auth_sysadmins_check
        t['auth_allow_anonymous_access'] = logic.auth_allow_anonymous_access
        t['auth_disallow_anonymous_access'] = (
            logic.auth_disallow_anonymous_access
        )
        t['mail_recipient'] = mailer.mail_recipient
        t['mail_user'] = mailer.mail_user

        # class functions
        t['render_snippet'] = self._render_snippet
        t['add_template_directory'] = self._add_template_directory
        t['add_public_directory'] = self._add_public_directory
        t['add_resource'] = self._add_resource
        t['add_ckan_admin_tab'] = self._add_ckan_admin_tabs
        t['requires_ckan_version'] = self._requires_ckan_version
        t['check_ckan_version'] = self._check_ckan_version
        t['get_endpoint'] = self._get_endpoint
        t['CkanVersionException'] = CkanVersionException
        t['HelperError'] = HelperError
        t['enqueue_job'] = enqueue_job

        if six.PY2:
            t['response'] = pylons.response
            self.docstring_overrides['response'] = '''
The Pylons response object.

Pylons uses this object to generate the HTTP response it returns to the web
browser. It has attributes like the HTTP status code, the response headers,
content type, cookies, etc.

'''
            t['BaseController'] = base.BaseController
            # TODO: Sort these out
            t['CkanCommand'] = old_cli.CkanCommand
            t['load_config'] = old_cli.load_config

        # check contents list correct
        errors = set(t).symmetric_difference(set(self.contents))
        if errors:
            raise Exception('Plugin toolkit error %s not matching' % errors)

    # wrappers
    # Wrapper for the render_snippet function as it uses keywords rather than
    # dict to pass data.
    @classmethod
    def _render_snippet(cls, template, data=None):
        '''Render a template snippet and return the output.

        See :doc:`/theming/index`.

        '''
        data = data or {}
        return cls.base.render_snippet(template, **data)

    # new functions
    @classmethod
    def _add_template_directory(cls, config, relative_path):
        '''Add a path to the :ref:`extra_template_paths` config setting.

        The path is relative to the file calling this function.

        '''
        cls._add_served_directory(config, relative_path,
                                  'extra_template_paths')

    @classmethod
    def _add_public_directory(cls, config, relative_path):
        '''Add a path to the :ref:`extra_public_paths` config setting.

        The path is relative to the file calling this function.

        Webassets addition: append directory to webassets load paths
        in order to correctly rewrite relative css paths and resolve
        public urls.

        '''
        import ckan.lib.helpers as h
        from ckan.lib.webassets_tools import add_public_path
        path = cls._add_served_directory(
            config,
            relative_path,
            'extra_public_paths'
        )
        url = h._local_url('/', locale='default')
        add_public_path(path, url)

    @classmethod
    def _add_served_directory(cls, config, relative_path, config_var):
        ''' Add extra public/template directories to config. '''
        import inspect
        import os

        assert config_var in ('extra_template_paths', 'extra_public_paths')
        # we want the filename that of the function caller but they will
        # have used one of the available helper functions
        # TODO: starting from python 3.5, `inspect.stack` returns list
        # of named tuples `FrameInfo`. Don't forget to remove
        # `getframeinfo` wrapper after migration.
        filename = inspect.getframeinfo(inspect.stack()[2][0]).filename

        this_dir = os.path.dirname(filename)
        absolute_path = os.path.join(this_dir, relative_path)
        if absolute_path not in config.get(config_var, '').split(','):
            if config.get(config_var):
                config[config_var] += ',' + absolute_path
            else:
                config[config_var] = absolute_path
        return absolute_path

    @classmethod
    def _add_resource(cls, path, name):
        '''Add a WebAssets library to CKAN.

        WebAssets libraries are directories containing static resource
        files (e.g. CSS, JavaScript or image files) that can be
        compiled into WebAsset Bundles.

        See :doc:`/theming/index` for more details.

        '''
        import inspect
        import os
        from ckan.lib.webassets_tools import create_library

        # we want the filename that of the function caller but they
        # will have used one of the available helper functions
        # TODO: starting from python 3.5, `inspect.stack` returns list
        # of named tuples `FrameInfo`. Don't forget to remove
        # `getframeinfo` wrapper after migration.
        filename = inspect.getframeinfo(inspect.stack()[1][0]).filename

        this_dir = os.path.dirname(filename)
        absolute_path = os.path.join(this_dir, path)
        create_library(name, absolute_path)

        import six
        if six.PY2:
            # TODO: remove next two lines after dropping Fanstatic support
            import ckan.lib.fanstatic_resources
            ckan.lib.fanstatic_resources.create_library(name, absolute_path)

    @classmethod
    def _add_ckan_admin_tabs(cls, config, route_name, tab_label,
                             config_var='ckan.admin_tabs', icon=None):
        '''
        Update 'ckan.admin_tabs' dict the passed config dict.
        '''
        # get the admin_tabs dict from the config, or an empty dict.
        admin_tabs_dict = config.get(config_var, {})
        # update the admin_tabs dict with the new values
        admin_tabs_dict.update({
            route_name: {
                'label': tab_label,
                'icon': icon
            }
        })
        # update the config with the updated admin_tabs dict
        config.update({config_var: admin_tabs_dict})

    @classmethod
    def _version_str_2_list(cls, v_str):
        ''' convert a version string into a list of ints
        eg 1.6.1b --> [1, 6, 1] '''
        import re
        v_str = re.sub(r'[^0-9.]', '', v_str)
        return [int(part) for part in v_str.split('.')]

    @classmethod
    def _check_ckan_version(cls, min_version=None, max_version=None):
        '''Return ``True`` if the CKAN version is greater than or equal to
        ``min_version`` and less than or equal to ``max_version``,
        return ``False`` otherwise.

        If no ``min_version`` is given, just check whether the CKAN version is
        less than or equal to ``max_version``.

        If no ``max_version`` is given, just check whether the CKAN version is
        greater than or equal to ``min_version``.

        :param min_version: the minimum acceptable CKAN version,
            eg. ``'2.1'``
        :type min_version: string

        :param max_version: the maximum acceptable CKAN version,
            eg. ``'2.3'``
        :type max_version: string

        '''
        current = cls._version_str_2_list(cls.ckan.__version__)

        if min_version:
            min_required = cls._version_str_2_list(min_version)
            if current < min_required:
                return False
        if max_version:
            max_required = cls._version_str_2_list(max_version)
            if current > max_required:
                return False
        return True

    @classmethod
    def _requires_ckan_version(cls, min_version, max_version=None):
        '''Raise :py:exc:`~ckan.plugins.toolkit.CkanVersionException` if the
        CKAN version is not greater than or equal to ``min_version`` and
        less then or equal to ``max_version``.

        If no ``max_version`` is given, just check whether the CKAN version is
        greater than or equal to ``min_version``.

        Plugins can call this function if they require a certain CKAN version,
        other versions of CKAN will crash if a user tries to use the plugin
        with them.

        :param min_version: the minimum acceptable CKAN version,
            eg. ``'2.1'``
        :type min_version: string

        :param max_version: the maximum acceptable CKAN version,
            eg. ``'2.3'``
        :type max_version: string

        '''
        from ckan.exceptions import CkanVersionException
        if not cls._check_ckan_version(min_version=min_version,
                                       max_version=max_version):
            if not max_version:
                error = 'Requires ckan version %s or higher' % min_version
            else:
                error = 'Requires ckan version between {0} and {1}'.format(
                    min_version,
                    max_version
                )
            raise CkanVersionException(error)

    @classmethod
    def _get_endpoint(cls):
        """Returns tuple in format: (controller|blueprint, action|view).
        """
        import ckan.common as common
        try:
            # CKAN >= 2.8
            endpoint = tuple(common.request.endpoint.split('.'))
        except AttributeError:
            try:
                return common.c.controller, common.c.action
            except AttributeError:
                return (None, None)
        # service routes, like `static`
        if len(endpoint) == 1:
            return endpoint + ('index', )
        return endpoint

    def __getattr__(self, name):
        ''' return the function/object requested '''
        if not self._toolkit:
            self._initialize()
        if name in self._toolkit:
            return self._toolkit[name]
        else:
            if name == '__bases__':
                return self.__class__.__bases__
            raise AttributeError('`%s` not found in plugins toolkit' % name)

    def __dir__(self):
        if not self._toolkit:
            self._initialize()
        return sorted(self._toolkit.keys())


# https://mail.python.org/pipermail/python-ideas/2012-May/014969.html
sys.modules[__name__] = _Toolkit()
