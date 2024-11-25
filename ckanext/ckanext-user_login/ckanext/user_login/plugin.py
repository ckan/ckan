import ckan.plugins as p
from .logic.actions import login_activity_show
from .logic import auth


class UserLoginPlugin(p.SingletonPlugin):
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)

    def get_actions(self):
        return {
            'login_activity_show': login_activity_show,
        }

    def get_auth_functions(self):
        return auth.get_auth_functions()