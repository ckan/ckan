import inspect
import os
import re

import pylons
import paste.deploy.converters as converters
import webhelpers.html.tags

__all__ = ['toolkit']


class CkanVersionException(Exception):
    ''' Exception raised if required ckan version is not available. '''
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
        'check_access',         # check logic function authorisation
        'ObjectNotFound',       # action not found exception
                                # (ckan.logic.NotFound)
        'NotAuthorized',        # action not authorized exception
        'ValidationError',      # model update validation error
        'CkanCommand',          # class for providing cli interfaces

        ## Fully defined in this file ##
        'add_template_directory',
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
        import ckan.lib.cli as cli

        # Allow class access to these modules
        self.__class__.ckan = ckan
        self.__class__.base = base

        t = self._toolkit

        # imported functions
        t['_'] = pylons.i18n._
        t['c'] = pylons.c
        t['request'] = pylons.request
        t['render'] = base.render
        t['render_text'] = base.render_text
        t['asbool'] = converters.asbool
        t['asint'] = converters.asint
        t['aslist'] = converters.aslist
        t['literal'] = webhelpers.html.tags.literal

        t['get_action'] = logic.get_action
        t['check_access'] = logic.check_access
        t['ObjectNotFound'] = logic.NotFound  # Name change intentional
        t['NotAuthorized'] = logic.NotAuthorized
        t['ValidationError'] = logic.ValidationError

        t['CkanCommand'] = cli.CkanCommand

        # class functions
        t['render_snippet'] = self._render_snippet
        t['add_template_directory'] = self._add_template_directory
        t['add_public_directory'] = self._add_public_directory
        t['requires_ckan_version'] = self._requires_ckan_version
        t['check_ckan_version'] = self._check_ckan_version
        t['CkanVersionException'] = CkanVersionException

        # check contents list correct
        errors = set(t).symmetric_difference(set(self.contents))
        if errors:
            raise Exception('Plugin toolkit error %s not matching' % errors)

    # wrappers
    @classmethod
    def _render_snippet(cls, template, data=None):
        ''' helper for the render_snippet function as it uses keywords
        rather than dict to pass data '''
        data = data or {}
        return cls.base.render_snippet(template, **data)

    # new functions
    @classmethod
    def _add_template_directory(cls, config, relative_path):
        ''' Function to aid adding extra template paths to the config.
        The path is relative to the file calling this function. '''
        cls._add_served_directory(config, relative_path,
                                  'extra_template_paths')

    @classmethod
    def _add_public_directory(cls, config, relative_path):
        ''' Function to aid adding extra public paths to the config.
        The path is relative to the file calling this function. '''
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
    def _version_str_2_list(cls, v_str):
        ''' convert a version string into a list of ints
        eg 1.6.1b --> [1, 6, 1] '''
        v_str = re.sub(r'[^0-9.]', '', v_str)
        return [int(part) for part in v_str.split('.')]

    @classmethod
    def _check_ckan_version(cls, min_version=None, max_version=None):
        ''' Check that the ckan version is correct for the plugin. '''
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
        ''' Check that the ckan version is correct for the plugin. '''
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

toolkit = _Toolkit()
del _Toolkit
