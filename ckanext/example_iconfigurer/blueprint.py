# encoding: utf-8

import ckan.lib.base as base
import ckan.lib.helpers as helpers
from flask import Blueprint
render = base.render

example_iconfigurer = Blueprint('example_iconfigurer', __name__)


def config_one():
    '''Render the config template with the first custom title.'''

    return render(
        'admin/myext_config.html',
        extra_vars={'title': 'My First Config Page'}
    )


def config_two():
    '''Render the config template with the second custom title.'''
    return render(
        'admin/myext_config.html',
        extra_vars={'title': 'My Second Config Page'}
    )


def build_extra_admin_nav():
    '''Return results of helpers.build_extra_admin_nav for testing.'''
    return helpers.build_extra_admin_nav()


example_iconfigurer.add_url_rule(
    '/ckan-admin/myext_config_one', view_func=config_one
)
example_iconfigurer.add_url_rule(
    '/ckan-admin/myext_config_two', view_func=config_two
)
example_iconfigurer.add_url_rule(
    '/build_extra_admin_nav', view_func=build_extra_admin_nav
)
