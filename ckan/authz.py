import sqlalchemy as sa

import ckan.model as model

class Blacklister(object):
    '''Blacklist by username.

    NB: username will be IP address if user not logged in.
    '''

    @staticmethod
    def is_blacklisted(username):
        from pylons import config
        blacklist_string = config.get('auth.blacklist', '')
        blacklisted = blacklist_string.split()
        if username in blacklisted:
            return True
        else:
            return False


class Authorizer(object):
    '''An access controller.
    '''
    blacklister = Blacklister

    @classmethod
    def am_authorized(cls, c, action, domain_object):
        username = c.user or c.author
        return cls.is_authorized(username, action, domain_object)

    @classmethod
    def is_authorized(cls, username, action, domain_object):
        if isinstance(username, str):
            username = username.decode('utf8')
        assert isinstance(username, unicode), type(username)
        assert model.Action.is_valid(action), action
        assert isinstance(domain_object, model.DomainObject)

        from pylons import config
        # sysadmins can do everything
        admins_string = config.get('auth.sysadmins', '')
        admins = admins_string.split()
        if username in admins:
            return True

        if action is not model.Action.READ:
            if cls.blacklister.is_blacklisted(username):
                return False

        roles = cls.get_roles(username, domain_object)
        if not roles:
            # print "No roles"
            return False

        # print '%r has roles %s on object %s. Checking permission to %s' % (username, roles, domain_object.name, action)
        if model.Role.ADMIN in roles:
            # print "Admin"
            return True
        for role in roles:
            action_query = model.RoleAction.query.filter_by(role=role,
                                                            action=action)
            if action_query.count() > 0:
                # print "Action query", action_query.all()
                return True

        return False

    @classmethod
    def get_package_roles_printable(cls, domain_obj):
        prs = cls.get_package_roles(domain_obj)
        printable_prs = []
        for user, role in prs:
            printable_prs.append('%s - \t%s' % (user.name, role))
        return '%s roles:\n' % domain_obj.name + '\n'.join(printable_prs)        

    @classmethod
    def get_package_roles(cls, domain_obj):
        # returns the roles for all users on the specified domain object
        assert isinstance(domain_obj, model.Package)
        q = cls._get_package_roles_query(domain_obj)
        prs = []
        for pr in q.all():
            user = model.Session.get(model.User, pr.user_id)
            prs.append((user, pr.role))
        return prs

    @classmethod
    def get_roles(cls, username, domain_obj):
        # returns the roles that the specified user has on the
        # specified domain object
        assert isinstance(username, unicode), repr(username)
        assert isinstance(domain_obj, model.Package)

        # get roles for this package
        q = cls._get_package_roles_query(domain_obj)

        # filter by user and pseudo-users
        user = model.User.by_name(username)
        visitor = model.User.by_name(model.PSEUDO_USER__VISITOR)
        logged_in = model.User.by_name(model.PSEUDO_USER__LOGGED_IN)
        if username == model.PSEUDO_USER__VISITOR or not user:
            # visitor (not logged in)
            q = q.filter(model.UserObjectRole.user_id==visitor.id)
        else:
            # logged in user
            q = q.filter(sa.or_(
                model.UserObjectRole.user_id==user.id,
                model.UserObjectRole.user_id==logged_in.id,
                model.UserObjectRole.user_id==visitor.id,
                ))

        prs = q.all()
        return [pr.role for pr in prs]

    @classmethod
    def _get_package_roles_query(cls, domain_obj):
        assert isinstance(domain_obj, model.Package)

        if isinstance(domain_obj, model.Package):
            q = model.PackageRole.query.filter_by(package_id=domain_obj.id)
        else:
            raise NotImplementedError()
        return q        
