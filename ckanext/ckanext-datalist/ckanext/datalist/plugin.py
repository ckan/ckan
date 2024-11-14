import ckan.plugins as p
from .logic.actions import resources_statistics, users_statistics
from .logic import auth

class DatalistPlugin(p.SingletonPlugin): 
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)

    def get_actions(self):
        return {
            'stats_resources': resources_statistics,
            'stats_users': users_statistics,
        }

    def get_auth_functions(self):
        return auth.get_auth_functions()
