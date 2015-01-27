import sys
from pprint import pprint

from ckan.lib.commands import CkanCommand


class UserCmd(CkanCommand):
    '''Manage users

    Usage:
      user                            - lists users
      user list                       - lists users
      user USERNAME                   - shows user properties
      user add USERNAME [FIELD1=VALUE1 FIELD2=VALUE2 ...]
                                      - add a user (prompts for password
                                        if not supplied).
                                        Field can be: apikey
                                                      password
                                                      email
      user setpass USERNAME           - set user password (prompts)
      user remove USERNAME            - removes user from users
      user search QUERY               - searches for a user name
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = None
    min_args = 0

    def command(self):
        self._load_config()

        if not self.args:
            self.list()
        else:
            cmd = self.args[0]
            if cmd == 'add':
                self.add()
            elif cmd == 'remove':
                self.remove()
            elif cmd == 'search':
                self.search()
            elif cmd == 'setpass':
                self.setpass()
            elif cmd == 'list':
                self.list()
            else:
                self.show()

    def get_user_str(self, user):
        user_str = 'name=%s' % user.name
        if user.name != user.display_name:
            user_str += ' display=%s' % user.display_name
        return user_str

    def list(self):
        import ckan.model as model
        print 'Users:'
        users = model.Session.query(model.User).filter_by(state='active')
        print 'count = %i' % users.count()
        for user in users:
            print self.get_user_str(user)

    def show(self):
        import ckan.model as model

        username = self.args[0]
        user = model.User.get(unicode(username))
        print 'User: \n', user

    def setpass(self):
        import ckan.model as model

        if len(self.args) < 2:
            print 'Need name of the user.'
            return
        username = self.args[1]
        user = model.User.get(username)
        print('Editing user: %r' % user.name)

        password = self.password_prompt()
        user.password = password
        model.repo.commit_and_remove()
        print 'Done'

    def search(self):
        import ckan.model as model

        if len(self.args) < 2:
            print 'Need user name query string.'
            return
        query_str = self.args[1]

        query = model.User.search(query_str)
        print '%i users matching %r:' % (query.count(), query_str)
        for user in query.all():
            print self.get_user_str(user)

    @classmethod
    def password_prompt(cls):
        import getpass
        password1 = None
        while not password1:
            password1 = getpass.getpass('Password: ')
        password2 = getpass.getpass('Confirm password: ')
        if password1 != password2:
            print 'Passwords do not match'
            sys.exit(1)
        return password1

    def add(self):
        import ckan.model as model

        if len(self.args) < 2:
            print 'Need name of the user.'
            sys.exit(1)
        username = self.args[1]

        # parse args into data_dict
        data_dict = {'name': username}
        for arg in self.args[2:]:
            try:
                field, value = arg.split('=', 1)
                data_dict[field] = value
            except ValueError:
                raise ValueError('Could not parse arg: %r '
                                 '(expected "<option>=<value>)"' % arg)

        if 'password' not in data_dict:
            data_dict['password'] = self.password_prompt()

        print('Creating user: %r' % username)

        try:
            import ckan.logic as logic
            f = logic.get_action('get_site_user')
            site_user = f({'model': model, 'ignore_auth': True}, {})
            context = {'model': model,
                       'session': model.Session,
                       'ignore_auth': True,
                       'user': site_user['name'],
                       }
            user_dict = logic.get_action('user_create')(context, data_dict)
            pprint(user_dict)
        except logic.ValidationError, e:
            print e
            sys.exit(1)

    def remove(self):
        import ckan.model as model

        if len(self.args) < 2:
            print 'Need name of the user.'
            return
        username = self.args[1]

        user = model.User.by_name(unicode(username))
        if not user:
            print 'Error: user "%s" not found!' % username
            return
        user.delete()
        model.repo.commit_and_remove()
        print('Deleted user: %s' % username)
