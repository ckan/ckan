## This file is intended to make functions consistently available to
## plugins whilst giving developers the ability move code around or
## change underlying frameworks etc. It should not be used internaly
## within ckan only by extensions. Functions should only be removed from
## this file after reasonable depreciation notice has been given.

import inspect
import os

import pylons
import paste.deploy.converters as converters
import webhelpers.html.tags

import lib.base as base


__all__ = [
    ## Imported functions ##
    'c',                    # template context
    'request',              # http request object
    'render',               # template render function
    'render_text',          # Genshi NewTextTemplate render function
    'render_snippet',       # snippet render function
    'asbool',               # converts an object to a boolean
    'asint',                # converts an object to an integer
    'aslist',               # converts an object to a list
    'literal',              # stop tags in a string being escaped

    ## Functions fully defined here ##
    'add_template_directory',
    'add_public_directory',
]

c = pylons.c
request = pylons.request
render = base.render
render_text = base.render_text
asbool = converters.asbool
asint = converters.asint
aslist = converters.aslist
literal = webhelpers.html.tags.literal


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
