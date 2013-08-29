import inspect
import os
import re

import paste.deploy.converters as converters
import webhelpers.html.tags

__all__ = ['toolkit']


class CkanVersionException(Exception):
    '''Exception raised by
    :py:func:`~ckan.plugins.toolkit.requires_ckan_version` if the required CKAN
    version is not available.

    '''
    pass


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
        ## Imported functions/objects ##
        '_',                    # i18n translation
        'c',                    # template context
        'request',              # http request object
        'render',               # template render function
        'render_text',          # Genshi NewTextTemplate render function
        'render_snippet',       # snippet render function
        'asbool',               # converts an object to a boolean
        'asint',                # converts an object to an integer
        'aslist',               # converts an object to a list
        'literal',              # stop tags in a string being escaped
        'get_action',           # get logic action function
        'get_converter',        # get validator function
        'get_validator',        # get convertor action function
        'check_access',         # check logic function authorisation
        'ObjectNotFound',       # action not found exception
                                # (ckan.logic.NotFound)
        'NotAuthorized',        # action not authorized exception
        'UnknownConverter',     # convertor not found exception
        'UnknownValidator',     # validator not found exception
        'ValidationError',      # model update validation error
        'Invalid',              # validation invalid exception
        'CkanCommand',          # class for providing cli interfaces
        'DefaultDatasetForm',   # base class for IDatasetForm plugins
        'response',             # response object for cookies etc
        'BaseController',       # Allow controllers to be created
        'abort',                # abort actions
        'redirect_to',          # allow redirections
        'url_for',              # create urls
        'get_or_bust',          # helpful for actions
        'side_effect_free',     # actions can be accessed via api
        'auth_sysadmins_check', # allow auth functions to be checked for sysadmins

        ## Fully defined in this file ##
        'add_template_directory',
        'add_resource',
        'add_public_directory',
        'requires_ckan_version',
        'check_ckan_version',
        'CkanVersionException',
    ]

    def __init__(self):
        self._toolkit = {}

    def _initialize(self):
        ''' get the required functions/objects, store them for later
        access and check that they match the contents dict. '''

        import ckan
        import ckan.lib.base as base
        import ckan.logic as logic
        import ckan.logic.validators as logic_validators
        import ckan.lib.helpers as h
        import ckan.lib.cli as cli
        import ckan.lib.plugins as lib_plugins
        import ckan.common as common
        import pylons

        # Allow class access to these modules
        self.__class__.ckan = ckan
        self.__class__.base = base

        t = self._toolkit

        # imported functions
        t['_'] = common._
        t['c'] = common.c
        t['request'] = common.request
        t['render'] = base.render
        t['render_text'] = base.render_text
        t['asbool'] = converters.asbool
        t['asint'] = converters.asint
        t['aslist'] = converters.aslist
        t['literal'] = webhelpers.html.tags.literal

        t['get_action'] = logic.get_action
        t['get_converter'] = logic.get_converter
        t['get_validator'] = logic.get_validator
        t['check_access'] = logic.check_access
        t['ObjectNotFound'] = logic.NotFound  # Name change intentional
        t['NotAuthorized'] = logic.NotAuthorized
        t['ValidationError'] = logic.ValidationError
        t['UnknownConverter'] = logic.UnknownConverter
        t['UnknownValidator'] = logic.UnknownValidator
        t['Invalid'] = logic_validators.Invalid

        t['CkanCommand'] = cli.CkanCommand
        t['DefaultDatasetForm'] = lib_plugins.DefaultDatasetForm

        t['response'] = pylons.response
        t['BaseController'] = base.BaseController
        t['abort'] = base.abort
        t['redirect_to'] = h.redirect_to
        t['url_for'] = h.url_for
        t['get_or_bust'] = logic.get_or_bust
        t['side_effect_free'] = logic.side_effect_free
        t['auth_sysadmins_check'] = logic.auth_sysadmins_check

        # class functions
        t['render_snippet'] = self._render_snippet
        t['add_template_directory'] = self._add_template_directory
        t['add_public_directory'] = self._add_public_directory
        t['add_resource'] = self._add_resource
        t['requires_ckan_version'] = self._requires_ckan_version
        t['check_ckan_version'] = self._check_ckan_version
        t['CkanVersionException'] = CkanVersionException

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

        See :doc:`theming`.

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

        '''
        cls._add_served_directory(config, relative_path, 'extra_public_paths')

    @classmethod
    def _add_served_directory(cls, config, relative_path, config_var):
        ''' Add extra public/template directories to config. '''
        assert config_var in ('extra_template_paths', 'extra_public_paths')
        # we want the filename that of the function caller but they will
        # have used one of the available helper functions
        frame, filename, line_number, function_name, lines, index =\
            inspect.getouterframes(inspect.currentframe())[2]

        this_dir = os.path.dirname(filename)
        absolute_path = os.path.join(this_dir, relative_path)
        if absolute_path not in config.get(config_var, ''):
            if config.get(config_var):
                config[config_var] += ',' + absolute_path
            else:
                config[config_var] = absolute_path

    @classmethod
    def _add_resource(cls, path, name):
        '''Add a Fanstatic resource library to CKAN.

        Fanstatic libraries are directories containing static resource files
        (e.g. CSS, JavaScript or image files) that can be accessed from CKAN.

        See :doc:`theming` for more details.

        '''
        # we want the filename that of the function caller but they will
        # have used one of the available helper functions
        frame, filename, line_number, function_name, lines, index =\
            inspect.getouterframes(inspect.currentframe())[1]

        this_dir = os.path.dirname(filename)
        absolute_path = os.path.join(this_dir, path)
        import ckan.lib.fanstatic_resources
        ckan.lib.fanstatic_resources.create_library(name, absolute_path)

    @classmethod
    def _version_str_2_list(cls, v_str):
        ''' convert a version string into a list of ints
        eg 1.6.1b --> [1, 6, 1] '''
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
        if not cls._check_ckan_version(min_version=min_version,
                                       max_version=max_version):
            if not max_version:
                error = 'Requires ckan version %s or higher' % min_version
            else:
                error = 'Requires ckan version between %s and %s' % \
                            (min_version, max_version)
            raise cls.CkanVersionException(error)

    def __getattr__(self, name):
        ''' return the function/object requested '''
        if not self._toolkit:
            self._initialize()
        if name in self._toolkit:
            return self._toolkit[name]
        else:
            if name == '__bases__':
                return self.__class__.__bases__
            raise Exception('`%s` not found in plugins toolkit' % name)

    def __dir__(self):
        if not self._toolkit:
            self._initialize()
        return sorted(self._toolkit.keys())


toolkit = _Toolkit()
del _Toolkit
