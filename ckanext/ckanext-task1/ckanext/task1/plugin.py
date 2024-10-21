# task1_plugin.py
import ckan.plugins as p
from .logic.actions import tracking_urls_and_counts
from .logic import auth


class Task1Plugin(p.SingletonPlugin):
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)

    def get_actions(self):
        return {
            'tracking_urls_and_counts': tracking_urls_and_counts
        }

    def get_auth_functions(self):
        return auth.get_auth_functions()
