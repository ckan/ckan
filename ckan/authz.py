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

        # sysadmins can do everything
        if cls.is_sysadmin(username):
            return True

        # check not blacklisted
        if action is not model.Action.READ:
            if cls.blacklister.is_blacklisted(username):
                return False

        # check this user's roles for this object
        roles = cls.get_roles(username, domain_object)
        if not roles:
            return False
        # print '%r has roles %s on object %s. Checking permission to %s' % (username, roles, domain_object.name, action)
        
        if model.Role.ADMIN in roles:
            return True

        # check it's active
        if hasattr(domain_object, 'state'):
            if domain_object.state != model.State.ACTIVE:
                return False

        # check if any of the roles allows the action requested
        for role in roles:
            action_query = model.Session.query(model.RoleAction).filter_by(
                role=role, action=action)
            if action_query.count() > 0:
                return True

        return False

    @classmethod
    def get_domain_object_roles_printable(cls, domain_obj):
        prs = cls.get_domain_object_roles(domain_obj)
        printable_prs = []
        for user, role in prs:
            printable_prs.append('%s - \t%s' % (user.name, role))
        return '%s roles:\n' % domain_obj.name + '\n'.join(printable_prs)        

    @classmethod
    def get_domain_object_roles(cls, domain_obj):
        '''Get a list of tuples (user, role) for domain_obj specified'''
        assert isinstance(domain_obj, (model.Package, model.Group))
        if isinstance(domain_obj, model.Package):
            q = model.Session.query(model.PackageRole).filter_by(package=domain_obj)
        elif isinstance(domain_obj, model.Group):
            q = model.Session.query(model.GroupRole).filter_by(group=domain_obj)
        prs = [ (pr.user, pr.role) for pr in q.all() ]
        return prs

    @classmethod
    def get_roles(cls, username, domain_obj):
        '''Get the roles that the specified user has on the specified domain
        object.
        '''
        assert isinstance(username, unicode), repr(username)

        # filter by user and pseudo-users
        user = model.User.by_name(username)
        visitor = model.User.by_name(model.PSEUDO_USER__VISITOR)
        logged_in = model.User.by_name(model.PSEUDO_USER__LOGGED_IN)
        q = cls._get_roles_query(domain_obj)
        if username == model.PSEUDO_USER__VISITOR or not user:
            q = q.filter_by(user=visitor)
        else:
            # logged in user
            q = q.filter(sa.or_(
                model.UserObjectRole.user==user,
                model.UserObjectRole.user==logged_in,
                model.UserObjectRole.user==visitor,
                ))
        prs = q.all()
        return [pr.role for pr in prs]

    @classmethod
    def is_sysadmin(cls, username):
        user = model.User.by_name(username)
        if user:
            q = model.Session.query(model.SystemRole).filter_by(role=model.Role.ADMIN, user=user)
            return q.count() > 0

    @classmethod
    def get_admins(cls, domain_obj):
        if isinstance(domain_obj, model.Package):
            q = model.Session.query(model.PackageRole).filter_by(package=domain_obj,
                                                  role=model.Role.ADMIN)
        elif isinstance(domain_obj, model.Group):
            q = model.Session.query(model.GroupRole).filter_by(group=domain_obj,
                                                role=model.Role.ADMIN)
        admins = [do_role.user for do_role in q.all()]
        return admins

    @classmethod
    def authorized_query(cls, username, entity):
        q = model.Session.query(entity)
        if username:
            user = model.User.by_name(username)
        else:
            user = None

        visitor = model.User.by_name(model.PSEUDO_USER__VISITOR)
        logged_in = model.User.by_name(model.PSEUDO_USER__LOGGED_IN)
        action = model.Action.READ

        if not cls.is_sysadmin(username):
            q = q.outerjoin('roles')
            if hasattr(entity, 'state'):
                state = entity.state
            else:
                state = model.State.ACTIVE
            if user:
                q = q.filter(sa.or_(model.UserObjectRole.user==user,
                                   model.UserObjectRole.user==visitor,
                                   model.UserObjectRole.user==logged_in))
                q = q.filter(sa.or_(
                    sa.and_(model.UserObjectRole.role==model.RoleAction.role,
                            model.RoleAction.action==action,
                            state==model.State.ACTIVE),
                    model.UserObjectRole.role==model.Role.ADMIN))
            else:
                q = q.filter(model.UserObjectRole.user==visitor)
                q = q.filter(
                    sa.and_(model.UserObjectRole.role==model.RoleAction.role,
                            model.RoleAction.action==action,
                            state==model.State.ACTIVE),
                    )
                
            q = q.distinct()

        return q

    @classmethod
    def _get_roles_query(cls, domain_obj):
        q = model.Session.query(model.UserObjectRole)
        is_a_class = domain_obj.__class__ == type
        context = domain_obj.__name__ if is_a_class else domain_obj.__class__.__name__
        q = q.filter_by(context=unicode(context))
        if not is_a_class:
            # this is kind of ugly as we have to switch on the instance type
            if isinstance(domain_obj, model.Package):
                q = q.with_polymorphic(model.PackageRole)
                q = q.filter(model.PackageRole.package==domain_obj)
            elif isinstance(domain_obj, model.Group):
                q = q.with_polymorphic(model.GroupRole)
                q = q.filter(model.GroupRole.group==domain_obj)
            else:
                raise Exception('Do not support context object like: %r' %
                        domain_obj)

        return q

        
