import sqlalchemy as sa
from sqlalchemy.orm.attributes import InstrumentedAttribute

import ckan.model as model
from ckan.plugins import PluginImplementations
from ckan.plugins.interfaces import IAuthorizer

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
    extensions = PluginImplementations(IAuthorizer)
    
    @classmethod
    def am_authorized(cls, c, action, domain_object):
        username = c.user or c.author
        return cls.is_authorized(username, action, domain_object)

    @classmethod
    def is_authorized(cls, username, action, domain_object):
        '''Authorize `action` by `username` on `domain_object`.
        
        :param username: a user identifier (may be e.g. an IP address).
        :param action: a ckan.model.authz.Action enumeration.
        :param domain_object: the domain object instance (or class/type in the
            case of e.g. 'create' action).

        :returns: True or False
        '''
        if isinstance(username, str):
            username = username.decode('utf8')
        assert isinstance(username, unicode), type(username)
        
        for extension in cls.extensions:
            authorized = extension.is_authorized(username,
                                                 action,
                                                 domain_object)
            if authorized:
                return True
        # sysadmins can do everything
        if cls.is_sysadmin(username) or domain_object is None:
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
        if domain_object.__class__ != type and hasattr(domain_object, 'state'):
            if domain_object.state == model.State.DELETED:
                return False

        # check if any of the roles allows the action requested
        for role in roles:
            action_query = model.Session.query(model.RoleAction).autoflush(False).filter_by(
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
        elif isinstance(domain_obj, model.AuthorizationGroup):
            q = model.Session.query(model.AuthorizationGroupRole).filter_by(authorization_group=domain_obj)
        prs = [ (pr.user, pr.role) for pr in q.all() ]
        return prs

    @classmethod
    def get_authorization_groups(cls, username):
        q = model.Session.query(model.AuthorizationGroup)
        q = q.autoflush(False)
        user = model.User.by_name(username, autoflush=False)
        if username == model.PSEUDO_USER__VISITOR or not user:
            q = q.filter(model.AuthorizationGroup.users.any(name=model.PSEUDO_USER__VISITOR))
        else:
            q = q.filter(model.AuthorizationGroup.users.any(
                            sa.or_(model.User.name==model.PSEUDO_USER__VISITOR,
                                   model.User.name==model.PSEUDO_USER__LOGGED_IN,
                                   model.User.name==username)))

        groups = q.all()
        for extension in cls.extensions:
            extra_groups = extension.get_authorization_groups(username)
            groups.extend(extra_groups)
        return groups

    @classmethod
    def get_roles(cls, username, domain_obj):
        '''Get the roles that the specified user has on the specified domain
        object.
        '''
        assert isinstance(username, unicode), repr(username)

        # filter by user and pseudo-users
        # TODO: these can be made into subqueries/joins! 
        user = model.User.by_name(username, autoflush=False)
        visitor = model.User.by_name(model.PSEUDO_USER__VISITOR, autoflush=False)
        q = cls._get_roles_query(domain_obj)
        q = q.autoflush(False)
        
        filters = [model.UserObjectRole.user==visitor]
        # check for groups:
        for authz_group in cls.get_authorization_groups(username):
            filters.append(model.UserObjectRole.authorized_group==authz_group)
        
        if (username != model.PSEUDO_USER__VISITOR) and (user is not None):
            logged_in = model.User.by_name(model.PSEUDO_USER__LOGGED_IN)
            filters.append(model.UserObjectRole.user==user)
            filters.append(model.UserObjectRole.user==logged_in)
        
        q = q.filter(sa.or_(*filters))
        return [pr.role for pr in q]
    
    @classmethod
    def is_sysadmin(cls, username):
        user = model.User.by_name(username, autoflush=False)
        if user:
            q = model.Session.query(model.SystemRole)
            q = q.autoflush(False)
            q = q.filter_by(role=model.Role.ADMIN, user=user)
            return q.count() > 0

    @classmethod
    def get_admins(cls, domain_obj):
        if isinstance(domain_obj, model.Package):
            q = model.Session.query(model.PackageRole).filter_by(package=domain_obj,
                                                  role=model.Role.ADMIN)
        elif isinstance(domain_obj, model.Group):
            q = model.Session.query(model.GroupRole).filter_by(group=domain_obj,
                                                role=model.Role.ADMIN)
        elif isinstance(domain_obj, model.AuthorizationGroup):
            q = model.Session.query(model.AuthorizationGroupRole).filter_by(authorization_group=domain_obj,
                                                role=model.Role.ADMIN)
        q = q.autoflush(False)
        admins = [do_role.user for do_role in q.all() if do_role.user]
        return admins

    @classmethod
    def authorized_query(cls, username, entity, action=model.Action.READ):
        q = model.Session.query(entity)
        q = q.autoflush(False)
        if username:
            user = model.User.by_name(username, autoflush=False)
        else:
            user = None
        visitor = model.User.by_name(model.PSEUDO_USER__VISITOR, autoflush=False)
        logged_in = model.User.by_name(model.PSEUDO_USER__LOGGED_IN,
                                       autoflush=False)
        if not cls.is_sysadmin(username):
            # This gets the role table the entity is joined to. we
            # need to use this in the queries below as if we use
            # model.UserObjectRole a cross join happens always
            # returning all the roles.  
            if hasattr(entity, 'continuity'):
                q = q.filter_by(current=True)
                q = q.outerjoin('continuity', 'roles')
                continuity = entity.continuity.property.mapper.class_
                role_cls = continuity.roles.property.mapper.class_ 
            else:
                role_cls = entity.roles.property.mapper.class_ 
                q = q.outerjoin('roles')

            if hasattr(entity, 'state'):
                state = entity.state
            else:
                state = None
                
            filters = [model.UserObjectRole.user==visitor]
            for authz_group in cls.get_authorization_groups(username):
                filters.append(role_cls.authorized_group==authz_group)
            if user:
                filters.append(role_cls.user==user)
                filters.append(role_cls.user==logged_in)
                q = q.filter(sa.or_(
                    sa.and_(role_cls.role==model.RoleAction.role,
                            model.RoleAction.action==action,
                            state and state!=model.State.DELETED),
                    role_cls.role==model.Role.ADMIN))
            else:
                q = q.filter(
                    sa.and_(role_cls.role==model.RoleAction.role,
                            model.RoleAction.action==action,
                            state and state!=model.State.DELETED),
                    )
            q = q.filter(sa.or_(*filters))   
            q = q.distinct()

        return q

    @classmethod
    def authorized_package_relationships(cls, username,
                                         package1,
                                         package2=None,
                                         relationship_type=None,
                                         action=model.Action.READ):
        '''For a given package(s) returns a list of relationships that
        the specified user is allowed to do the specified action on.'''
        # Maybe there is an sqlalchemy query to do this all in one, but
        # it would be rather complex.
        rels = package1.get_relationships(with_package=package2,
                                          type=relationship_type)
        authorized_rels = []
        for rel in rels:
            if cls.authorized_package_relationship(
                username, rel.subject, rel.object, action):
                authorized_rels.append(rel)
        return authorized_rels

    @classmethod
    def authorized_package_relationship(cls, username,
                                        package1,
                                        package2,
                                        action=model.Action.READ):
        '''Returns a boolean - whether a user is authorized to perform the
        specified action on a package relationship between the specified
        packages.'''
        return cls.is_authorized(username, action, package1) and \
               cls.is_authorized(username, action, package2)

    @classmethod
    def _get_roles_query(cls, domain_obj):
        q = model.Session.query(model.UserObjectRole)
        q = q.autoflush(False)
        is_a_class = domain_obj.__class__ == type
        if not is_a_class:
            # this is kind of ugly as we have to switch on the instance type
            if isinstance(domain_obj, model.Package):
                q = q.with_polymorphic(model.PackageRole)
                q = q.filter(model.PackageRole.package==domain_obj)
            elif isinstance(domain_obj, model.Group):
                q = q.with_polymorphic(model.GroupRole)
                q = q.filter(model.GroupRole.group==domain_obj)
            elif isinstance(domain_obj, model.AuthorizationGroup):
                q = q.with_polymorphic(model.AuthorizationGroupRole)
                q = q.filter(model.AuthorizationGroupRole.authorization_group==domain_obj)
            elif isinstance(domain_obj, model.System):
                q = q.with_polymorphic(model.SystemRole)
                q = q.filter(model.SystemRole.context==unicode(model.System.__name__))
            else:
                raise Exception('Do not support context object like: %r' %
                        domain_obj)
        context = domain_obj.__name__ if is_a_class else domain_obj.__class__.__name__
        q = q.filter_by(context=unicode(context))
        return q

        
