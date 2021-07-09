# encoding: utf-8

import os
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
