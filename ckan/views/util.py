# encoding: utf-8

import re

from flask import Blueprint

import ckan.lib.base as base

from ckan.common import g, config, _


util = Blueprint(u'util', __name__)


def primer():
    u''' Render all HTML components out onto a single page.
    This is useful for development/styling of CKAN. '''

    return base.render(u'development/primer.html')


util_rules = [
    (u'/testing/primer', primer),
]

for rule, view_func in util_rules:
    util.add_url_rule(rule, view_func=view_func)
