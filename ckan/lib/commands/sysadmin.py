from ckan.lib.commands import CkanCommand
from ckan.lib.commands.user import UserCmd


class Sysadmin(CkanCommand):
    '''Gives sysadmin rights to a named user

    Usage:
      sysadmin                      - lists sysadmins
      sysadmin list                 - lists sysadmins
      sysadmin add USERNAME         - add a user as a sysadmin
      sysadmin remove USERNAME      - removes user from sysadmins
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 2
    min_args = 0

    def command(self):
        self._load_config()

        cmd = self.args[0] if self.args else None
        if not cmd or cmd == 'list':
            self.list()
        elif cmd == 'add':
            self.add()
        elif cmd == 'remove':
            self.remove()
        else:
            print 'Command %s not recognized' % cmd

    def list(self):
        import ckan.model as model
        print 'Sysadmins:'
        sysadmins = model.Session.query(model.User).filter_by(sysadmin=True)
        print 'count = %i' % sysadmins.count()
        for sysadmin in sysadmins:
            print '%s name=%s id=%s' % (sysadmin.__class__.__name__,
                                        sysadmin.name,
                                        sysadmin.id)

    def add(self):
        import ckan.model as model

        if len(self.args) < 2:
            print 'Need name of the user to be made sysadmin.'
            return
        username = self.args[1]

        user = model.User.by_name(unicode(username))
        if not user:
            print 'User "%s" not found' % username
            makeuser = raw_input('Create new user: %s? [y/n]' % username)
            if makeuser == 'y':
                password = UserCmd.password_prompt()
                print('Creating %s user' % username)
                user = model.User(name=unicode(username),
                                  password=password)
            else:
                print 'Exiting ...'
                return

        user.sysadmin = True
        model.Session.add(user)
        model.repo.commit_and_remove()
        print 'Added %s as sysadmin' % username

    def remove(self):
        import ckan.model as model

        if len(self.args) < 2:
            print 'Need name of the user to be made sysadmin.'
            return
        username = self.args[1]

        user = model.User.by_name(unicode(username))
        if not user:
            print 'Error: user "%s" not found!' % username
            return
        user.sysadmin = False
        model.repo.commit_and_remove()
