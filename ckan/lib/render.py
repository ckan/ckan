# encoding: utf-8

import os
import re
import logging

from ckan.common import config

log = logging.getLogger(__name__)

_template_info_cache = {}

def reset_template_info_cache():
    '''Reset the template cache'''
    _template_info_cache.clear()

def find_template(template_name):
    ''' looks through the possible template paths to find a template
    returns the full path is it exists. '''
    template_paths = config['computed_template_paths']
    for path in template_paths:
        if os.path.exists(os.path.join(path, template_name.encode('utf-8'))):
            return os.path.join(path, template_name)

def template_type(template_path):
    return 'jinja2'

class TemplateNotFound(Exception):
    pass

def template_info(template_name):
    ''' Returns the path and type for a template '''

    if template_name in _template_info_cache:
        t_data = _template_info_cache[template_name]
        return t_data['template_path'], t_data['template_type']

    template_path = find_template(template_name)
    if not template_path:
        raise TemplateNotFound('Template %s cannot be found' % template_name)
    t_type = template_type(template_path)

    # if in debug mode we always want to search for templates so we
    # don't want to store it.
    if not config.get('debug', False):
        t_data = {'template_path' : template_path,
                  'template_type' : t_type,}
        _template_info_cache[template_name] = t_data
    return template_path, t_type
