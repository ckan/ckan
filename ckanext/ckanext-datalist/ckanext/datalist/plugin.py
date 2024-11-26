import ckan.plugins as p
from .logic.actions import resources_statistics, users_statistics, new_users_statistics
from .logic import auth
import ckan.plugins.toolkit as toolkit
import ckanext.datalist.views as views


class DatalistPlugin(p.SingletonPlugin): 
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IBlueprint)
   
    def get_blueprint(self):
        return views.get_blueprints()

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')
        toolkit.add_resource('public', 'mycharts')

    def get_actions(self):
        return {
            'stats_resources': resources_statistics,
            'stats_users': users_statistics,
            'stats_new_users': new_users_statistics,
        }

    def get_auth_functions(self):
        return auth.get_auth_functions()
