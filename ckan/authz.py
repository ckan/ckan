class Action(object):
    
    def __init__(self, name):
        self.name = name

actions = {
        'revision-purge' : Action('revision-purge'),
        }


class Authorizer(object):
    '''A very basic access controller.

    In future expand this to have roles, permissions etc.
    '''

    def is_authorized(self, username, action):
        from pylons import config
        admins_string = config.get('auth.admins', '')
        admins = admins_string.split()
        if username in admins:
            return True
        else:
            return False

