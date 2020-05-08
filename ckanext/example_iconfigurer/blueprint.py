# encoding: utf-8

import ckan.lib.base as base
import ckan.lib.helpers as helpers
from flask import Blueprint
render = base.render

example_iconfigurer = Blueprint(u'example_iconfigurer', __name__)


def config_one():
    u'''Render the config template with the first custom title.'''

    return render(
        u'admin/myext_config.html',
        extra_vars={u'title': u'My First Config Page'}
    )


def config_two():
    u'''Render the config template with the second custom title.'''
    return render(
        u'admin/myext_config.html',
        extra_vars={u'title': u'My Second Config Page'}
    )


def build_extra_admin_nav():
    u'''Return results of helpers.build_extra_admin_nav for testing.'''
    return helpers.build_extra_admin_nav()


example_iconfigurer.add_url_rule(
    u'/ckan-admin/myext_config_one', view_func=config_one
)
example_iconfigurer.add_url_rule(
    u'/ckan-admin/myext_config_two', view_func=config_two
)
example_iconfigurer.add_url_rule(
    u'/build_extra_admin_nav', view_func=build_extra_admin_nav
)
