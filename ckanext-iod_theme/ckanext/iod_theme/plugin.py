# encoding: utf-8
import logging
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.common import config
import routes.mapper as mapper
import ckanext.iod_theme.helpers as h
from ckanext.iod_theme.logic.auth.update import has_user_permission_to_make_dataset_public

log = logging.getLogger(__name__)


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
        data_dict={'sort': 'name asc', 'all_fields': True})

    return groups


def register_translator():
    # Register a translator in this thread so that
    # the _() functions in logic layer can work
    from paste.registry import Registry
    from pylons import translator
    from ckan.lib.cli import MockTranslator
    global registry
    registry = Registry()
    registry.prepare()
    global translator_obj
    translator_obj = MockTranslator()
    registry.register(translator, translator_obj)


class Iod_ThemePlugin(plugins.SingletonPlugin):
    '''IOD theme plugin.

    '''
    plugins.implements(plugins.IConfigurer)
    # Declare that this plugin will implement ITemplateHelpers.
    plugins.implements(plugins.ITemplateHelpers)
    # Declare that this plugin will implement IActions
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IRoutes)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IFacets, inherit=True)

    startup = False

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'iod_theme')

    # ITemplateHelpers
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
                'iod_theme_get_user_role_role_in_org':
                    h.get_user_role_role_in_org,
                'iod_theme_create_geographic_strings':
                    h.create_geographic_strings,
                'iod_theme_free_tags_only':
                    h.free_tags_only,
                'theme_pagination':
                    h.theme_pagination
               }

    # Changing group icon WIP
    # map.redirect('/packages', '/dataset')
    # map.redirect('/packages/{url:.*}', '/dataset/{url}')
    # map.redirect('/package', '/dataset')
    # map.redirect('/package/{url:.*}', '/dataset/{url}')
    #
    # with SubMapper(map, controller='package') as m:
    #     m.connect('dataset_themes', '/dataset/themes/{id}',
    #           action='groups', ckan_icon='archive')
    #
    # map.redirect('/users/{url:.*}', '/user/{url}')
    # map.redirect('/user/', '/user')
    #
    # with SubMapper(map, controller='user') as m:
    #     m.connect('user_dashboard_themes', '/dashboard/themes',
    #           action='dashboard_groups', ckan_icon='archive')

    # IRoutes
    def before_map(self, map):

        map.connect('policy', '/policy', controller='home', action='policy')
        map.connect('use_cases', '/use_cases', controller='home', action='use_cases')

        group_controller = 'ckanext.iod_theme.controllers.theme:ThemeController'
        package_controller = 'ckanext.iod_theme.controllers.package:PackageController'

        map.connect('add dataset', '/dataset/new', controller=package_controller, action='new')
        map.connect('dataset_edit', '/dataset/edit/{id}', controller=package_controller,
                    action='edit',
                    ckan_icon='edit')

        map.redirect('/groups', '/theme',
                     _redirect_code='301 Moved Permanently')
        map.redirect('/groups/{url:.*}', '/theme/{url}',
                     _redirect_code='301 Moved Permanently')
        map.redirect('/group', '/theme',
                     _redirect_code='301 Moved Permanently')
        map.redirect('/group/{url:.*}', '/theme/{url}',
                     _redirect_code='301 Moved Permanently')
        map.redirect('/themes', '/theme',
                     _redirect_code='301 Moved Permanently')
        map.redirect('/themes/{url:.*}', '/theme/{url}',
                     _redirect_code='301 Moved Permanently')

        with mapper.SubMapper(map, controller=group_controller) as m:
            m.connect('theme_index', '/theme', action='index',
                      highlight_actions='index search')
            m.connect('theme_list', '/theme/list', action='list')
            m.connect('theme_new', '/theme/new', action='new')
            m.connect('theme_action', '/theme/{action}/{id}',
                      requirements=dict(action='|'.join([
                          'edit',
                          'delete',
                          'admins',
                          'member_new',
                          'member_delete',
                          'history'
                          'followers',
                          'follow',
                          'unfollow',
                          'admins',
                          'activity',
                      ])))
            m.connect('theme_about', '/theme/about/{id}',
                      action='about', ckan_icon='info-sign')
            m.connect('theme_edit', '/theme/edit/{id}',
                      action='edit', ckan_icon='edit')
            m.connect('theme_members', '/theme/edit_members/{id}',
                      action='members', ckan_icon='archive')
            m.connect('theme_activity', '/theme/activity/{id}/{offset}',
                      action='activity', ckan_icon='time')
            m.connect('theme_read', '/theme/{id}', action='read',
                      ckan_icon='sitemap')
        return map

    def after_map(self, map):
        return map

    # IActions
    def get_actions(self):
        module_root = 'ckanext.iod_theme.logic.action'
        action_functions = h._get_logic_functions(module_root)

        return action_functions

    # IAuthFunctions
    def get_auth_functions(self):
        return {
            'has_user_permission_to_make_dataset_public': has_user_permission_to_make_dataset_public
        }

    # IConfigurable
    def configure(self, config):
        self.startup = True
        register_translator()
        # Create geographic string vocabulary
        h.create_geographic_strings()
        self.startup = False

    # IFacets
    def dataset_facets(self, facets_dict, package_type):
        facets_dict['organization'] = toolkit._('Organizations')
        facets_dict.pop('organization')
        facets_dict['license_id'] = toolkit._('Licenses')
        facets_dict.pop('license_id')
        return facets_dict

    def group_facets(self, facets_dict, group_type, package_type):
        facets_dict['organization'] = toolkit._('Organizations')
        facets_dict.pop('organization')
        facets_dict['license_id'] = toolkit._('Licenses')
        facets_dict.pop('license_id')
        return facets_dict

    def organization_facets(self, facets_dict, organization_type, package_type):
        facets_dict['organization'] = toolkit._('Organizations')
        facets_dict.pop('organization')
        facets_dict['license_id'] = toolkit._('Licenses')
        facets_dict.pop('license_id')
        return facets_dict
