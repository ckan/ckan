class Action(object):
    
    def __init__(self, name):
        self.name = name

actions = {
        'revision-purge' : Action('revision-purge'),
        'package-update' : Action('package-update'),
        'package-create' : Action('package-create'),
        }

class Blacklister(object):
    '''Blacklist by username.

    NB: username will be IP address if user not logged in.
    '''

    def is_blacklisted(self, username):
        from pylons import config
        blacklist_string = config.get('auth.blacklist', '')
        blacklisted = blacklist_string.split()
        if username in blacklisted:
            return True
        else:
            return False


class Authorizer(object):
    '''A very basic access controller.

    In future expand this to have roles, permissions etc.
    '''
    blacklister = Blacklister()

    def is_authorized(self, username, action):
        from pylons import config
        # admins can do everything
        admins_string = config.get('auth.admins', '')
        admins = admins_string.split()
        if username in admins:
            return True

        if action.name in [ 'package-update', 'package-create']:
            if self.blacklister.is_blacklisted(username):
                return False
            else:
                return True

        return False


