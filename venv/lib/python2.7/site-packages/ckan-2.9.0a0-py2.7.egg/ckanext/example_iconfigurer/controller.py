# encoding: utf-8

import ckan.lib.base as base
import ckan.lib.helpers as helpers

render = base.render


class MyExtController(base.BaseController):

    def config_one(self):
        '''Render the config template with the first custom title.'''

        return render('admin/myext_config.html',
                      extra_vars={'title': 'My First Config Page'})

    def config_two(self):
        '''Render the config template with the second custom title.'''
        return render('admin/myext_config.html',
                      extra_vars={'title': 'My Second Config Page'})

    def build_extra_admin_nav(self):
        '''Return results of helpers.build_extra_admin_nav for testing.'''
        return helpers.build_extra_admin_nav()
