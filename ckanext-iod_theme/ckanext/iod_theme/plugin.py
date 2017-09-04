# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.common import config
import routes.mapper as mapper

def show_most_popular_groups():
    '''Return the value of the most_popular_groups config setting.

    To enable showing the most popular groups, add this line to the
    [app:main] section of your CKAN config file::

    ckan.iod_theme.show_most_popular_groups = True

    Returns ``False`` by default, if the setting is not in the config file.

    :rtype: boolean

    '''
    value = config.get('ckan.iod_theme.show_most_popular_groups', False)
    value = toolkit.asbool(value)
    return value


def most_popular_groups():
    '''Return a sorted list of the groups with the most datasets.'''

    # Get a list of all the site's groups from CKAN, sorted by number of
    # datasets.
    groups = toolkit.get_action('group_list')(
        data_dict={'sort': 'package_count desc', 'all_fields': True})

    # Truncate the list to the 10 most popular groups only.
    groups = groups[:10]

    return groups


class Iod_ThemePlugin(plugins.SingletonPlugin):
    '''IOD theme plugin.

    '''
    plugins.implements(plugins.IConfigurer)

    # Declare that this plugin will implement ITemplateHelpers.
    plugins.implements(plugins.ITemplateHelpers)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'iod_theme')

    def get_helpers(self):
        '''Register the most_popular_groups() function above as a template
        helper function.

        '''
        # Template helper function names should begin with the name of the
        # extension they belong to, to avoid clashing with functions from
        # other extensions.
        return {'iod_theme_most_popular_groups': most_popular_groups,
               'iod_theme_show_most_popular_groups':
               show_most_popular_groups,
               }

    plugins.implements(plugins.IRoutes)

    def before_map(self, map):
        map.redirect('/group', '/theme',
                     _redirect_code='301 Moved Permanently')
        map.redirect('/group/{url:.*}', '/theme/{url}',
                     _redirect_code='301 Moved Permanently')
        group_controller = 'ckan.controllers.group:GroupController'
        with mapper.SubMapper(map, controller=group_controller) as m:
            m.connect('theme_index', '/theme', action='index')
            m.connect('/theme/list', action='list')
            m.connect('/theme/new', action='new')
            m.connect('/theme/{action}/{id}',
                      requirements=dict(action='|'.join([
                          'delete',
                          'admins',
                          'member_new',
                          'member_delete',
                          'history'
                          'followers',
                          'follow',
                          'unfollow',
                      ])))
            m.connect('theme_activity', '/theme/activity/{id}',
                      action='activity', ckan_icon='time')
            m.connect('theme_read', '/theme/{id}', action='read')
            m.connect('theme_about', '/theme/about/{id}',
                      action='about', ckan_icon='info-sign')
            m.connect('theme_read', '/theme/{id}', action='read',
                      ckan_icon='sitemap')
            m.connect('theme_edit', '/theme/edit/{id}',
                      action='edit', ckan_icon='edit')
            m.connect('theme_members', '/theme/edit_members/{id}',
                      action='members', ckan_icon='group')
            m.connect('theme_bulk_process',
                      '/theme/bulk_process/{id}',
                      action='bulk_process', ckan_icon='sitemap')
        return map

    def after_map(self, map):
        return map
