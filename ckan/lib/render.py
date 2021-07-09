# encoding: utf-8

import os
import logging

from ckan.common import config

log = logging.getLogger(__name__)

_template_info_cache = {}

def reset_template_info_cache():
    '''Reset the template cache'''
    _template_info_cache.clear()


class TemplateNotFound(Exception):
    pass
