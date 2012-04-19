## This file is intended to make functions/objects consistently
## available to plugins whilst giving developers the ability move code
## around or change underlying frameworks etc. It should not be used
## internaly within ckan only by extensions. Functions should only be
## removed from this file after reasonable depreciation notice has
## been given.

import inspect
import os
import re

import pylons
import paste.deploy.converters as converters
import webhelpers.html.tags

import ckan
import ckan.lib.base as base
import ckan.logic as logic
import ckan.lib.cli as cli



__all__ = [
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
    'NotFound',             # action not found exception
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

_ = pylons.i18n._
c = pylons.c
request = pylons.request
render = base.render
render_text = base.render_text
asbool = converters.asbool
asint = converters.asint
aslist = converters.aslist
literal = webhelpers.html.tags.literal

get_action = logic.get_action
check_access = logic.check_access
NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError

CkanCommand = cli.CkanCommand

# wrappers
def render_snippet(template, data=None):
    data = data or {}
    return base.render_snippet(template, **data)


# new functions
def add_template_directory(config, relative_path):
    ''' Function to aid adding extra template paths to the config.
    The path is relative to the file calling this function. '''
    _add_served_directory(config, relative_path, 'extra_template_paths')

def add_public_directory(config, relative_path):
    ''' Function to aid adding extra public paths to the config.
    The path is relative to the file calling this function. '''
    _add_served_directory(config, relative_path, 'extra_public_paths')

def _add_served_directory(config, relative_path, config_var):
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

class CkanVersionException(Exception):
    ''' Exception raised if required ckan version is not available. '''
    pass


def _version_str_2_list(v_str):
    ''' conver a version string into a list of ints
    eg 1.6.1b --> [1, 6, 1] '''
    v_str = re.sub(r'[^0-9.]', '', v_str)
    return [int(part) for part in v_str.split('.')]

def check_ckan_version(min_version=None, max_version=None):
    ''' Check that the ckan version is correct for the plugin. '''
    current = _version_str_2_list(ckan.__version__)

    if min_version:
        min_required = _version_str_2_list(min_version)
        if current < min_required:
            return False
    if max_version:
        max_required = _version_str_2_list(max_version)
        if current > max_required:
            return False
    return True

def requires_ckan_version(min_version, max_version=None):
    ''' Check that the ckan version is correct for the plugin. '''
    if not check_ckan_version(min_version=min_version, max_version=max_version):
        if not max_version:
            error = 'Requires ckan version %s or higher' % min_version
        else:
            error = 'Requires ckan version  between %s and %s' % \
                        (min_version, max_version)
        raise CkanVersionException(error)
