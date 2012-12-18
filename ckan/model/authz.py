'''For an overview of CKAN authorization system and model see
doc/authorization.rst.

'''
import simplejson as json
import weakref

from sqlalchemy import orm, types, Column, Table, ForeignKey
from pylons import config

import meta
import core
import domain_object
import package as _package
import group
import user as _user
import types as _types

__all__ = ['NotRealUserException', 'Enum', 'Action', 'Role', 'RoleAction',
           'UserObjectRole', 'PackageRole', 'GroupRole',
           'SystemRole', 'PSEUDO_USER__VISITOR',
           'PSEUDO_USER__LOGGED_IN', 'init_authz_const_data',
           'init_authz_configuration_data', 'add_user_to_role',
           'setup_user_roles', 'setup_default_user_roles',
           'give_all_packages_default_user_roles',
           'user_has_role', 'remove_user_from_role', 'clear_user_roles']

PSEUDO_USER__LOGGED_IN = u'logged_in'
PSEUDO_USER__VISITOR = u'visitor'

class NotRealUserException(Exception):
    pass

## ======================================
## Action and Role Enums

class Enum(object):
    @classmethod
    def is_valid(cls, val):
        return val in cls.get_all()

    @classmethod
    def get_all(cls):
        if not hasattr(cls, '_all_items'):
            vals = []
            for key, val in cls.__dict__.items():
                if not key.startswith('_'):
                    vals.append(val)
            cls._all_items = vals
        return cls._all_items

class Action(Enum):
    EDIT = u'edit'
    CHANGE_STATE = u'change-state'
    READ = u'read'
    PURGE = u'purge'
    EDIT_PERMISSIONS = u'edit-permissions'
    PACKAGE_CREATE = u'create-package'
    GROUP_CREATE = u'create-group'
    SITE_READ = u'read-site'
    USER_READ = u'read-user'
    USER_CREATE = u'create-user'
    UPLOAD_ACTION = u'file-upload'

class Role(Enum):
    ADMIN = u'admin'
    EDITOR = u'editor'
    ANON_EDITOR = u'anon_editor'
    READER = u'reader'

# These define what is meant by 'editor' and 'reader' for all ckan
# instances - locked down or otherwise. They get refreshed on every db_upgrade.
# So if you want to lock down an ckan instance, change Visitor and LoggedIn
# to have a new role which for which you can allow your customised actions.
default_role_actions = [
    (Role.EDITOR, Action.EDIT),
    (Role.EDITOR, Action.PACKAGE_CREATE),
    (Role.EDITOR, Action.GROUP_CREATE),
    (Role.EDITOR, Action.USER_CREATE),
    (Role.EDITOR, Action.USER_READ),
    (Role.EDITOR, Action.SITE_READ),
    (Role.EDITOR, Action.READ),
    (Role.EDITOR, Action.UPLOAD_ACTION),
    (Role.ANON_EDITOR, Action.EDIT),
    (Role.ANON_EDITOR, Action.PACKAGE_CREATE),
    (Role.ANON_EDITOR, Action.USER_CREATE),
    (Role.ANON_EDITOR, Action.USER_READ),
    (Role.ANON_EDITOR, Action.SITE_READ),
    (Role.ANON_EDITOR, Action.READ),
    (Role.ANON_EDITOR, Action.UPLOAD_ACTION),
    (Role.READER, Action.USER_CREATE),
    (Role.READER, Action.USER_READ),
    (Role.READER, Action.SITE_READ),
    (Role.READER, Action.READ),
    ]


## ======================================
## Table Definitions

role_action_table = Table('role_action', meta.metadata,
           Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
           Column('role', types.UnicodeText),
           Column('context', types.UnicodeText, nullable=False),
           Column('action', types.UnicodeText),
           )

user_object_role_table = Table('user_object_role', meta.metadata,
           Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
           Column('user_id', types.UnicodeText, ForeignKey('user.id'), nullable=True),
#           Column('authorized_group_id', types.UnicodeText, ForeignKey('authorization_group.id'), nullable=True),
           Column('context', types.UnicodeText, nullable=False), # stores subtype
           Column('role', types.UnicodeText)
           )

package_role_table = Table('package_role', meta.metadata,
           Column('user_object_role_id', types.UnicodeText, ForeignKey('user_object_role.id'), primary_key=True),
           Column('package_id', types.UnicodeText, ForeignKey('package.id')),
           )

group_role_table = Table('group_role', meta.metadata,
           Column('user_object_role_id', types.UnicodeText, ForeignKey('user_object_role.id'), primary_key=True),
           Column('group_id', types.UnicodeText, ForeignKey('group.id')),
           )

system_role_table = Table('system_role', meta.metadata,
           Column('user_object_role_id', types.UnicodeText, ForeignKey('user_object_role.id'), primary_key=True),
           )


class RoleAction(domain_object.DomainObject):
    def __repr__(self):
        return '<%s role="%s" action="%s" context="%s">' % \
               (self.__class__.__name__, self.role, self.action, self.context)


# dictionary mapping protected objects (e.g. Package) to related ObjectRole
protected_objects = {}

class UserObjectRole(domain_object.DomainObject):
    name = None
    protected_object = None

    def __repr__(self):
        if self.user:
            return '<%s user="%s" role="%s" context="%s">' % \
                (self.__class__.__name__, self.user.name, self.role, self.context)
        else:
            assert False, "UserObjectRole is not a user"

    @classmethod
    def get_object_role_class(cls, domain_obj):
        protected_object = protected_objects.get(domain_obj.__class__, None)
        if protected_object is None:
            # TODO: make into an authz exception
            msg = '%s is not a protected object, i.e. a subject of authorization' % domain_obj
            raise Exception(msg)
        else:
            return protected_object

    @classmethod
    def user_has_role(cls, user, role, domain_obj):
        assert isinstance(user, _user.User), user
        q = cls._user_query(user, role, domain_obj)
        return q.count() == 1


    @classmethod
    def _user_query(cls, user, role, domain_obj):
        q = meta.Session.query(cls).filter_by(role=role)
        # some protected objects are not "contextual"
        if cls.name is not None:
            # e.g. filter_by(package=domain_obj)
            q = q.filter_by(**dict({cls.name: domain_obj}))
        q = q.filter_by(user=user)
        return q


    @classmethod
    def add_user_to_role(cls, user, role, domain_obj):
        '''NB: Leaves the caller to commit the change. If called twice without a
        commit, will add the role to the database twice. Since some other
        functions count the number of occurrences, that leaves a fairly obvious
        bug. But adding a commit here seems to break various tests.
        So don't call this twice without committing, I guess...
        '''
        # Here we're trying to guard against adding the same role twice, but
        # that won't work if the transaction hasn't been committed yet, which allows a role to be added twice (you can do this from the interface)
        if cls.user_has_role(user, role, domain_obj):
            return
        objectrole = cls(role=role, user=user)
        if cls.name is not None:
            setattr(objectrole, cls.name, domain_obj)
        meta.Session.add(objectrole)


    @classmethod
    def remove_user_from_role(cls, user, role, domain_obj):
        q = cls._user_query(user, role, domain_obj)
        for uo_role in q.all():
            meta.Session.delete(uo_role)
        meta.Session.commit()
        meta.Session.remove()


class PackageRole(UserObjectRole):
    protected_object = _package.Package
    name = 'package'

    def __repr__(self):
        if self.user:
            return '<%s user="%s" role="%s" package="%s">' % \
                (self.__class__.__name__, self.user.name, self.role, self.package.name)
        else:
            assert False, "%s is not a user" % self.__class__.__name__

protected_objects[PackageRole.protected_object] = PackageRole

class GroupRole(UserObjectRole):
    protected_object = group.Group
    name = 'group'

    def __repr__(self):
        if self.user:
            return '<%s user="%s" role="%s" group="%s">' % \
                (self.__class__.__name__, self.user.name, self.role, self.group.name)
        else:
            assert False, "%s is not a user" % self.__class__.__name__

protected_objects[GroupRole.protected_object] = GroupRole


class SystemRole(UserObjectRole):
    protected_object = core.System
    name = None
protected_objects[SystemRole.protected_object] = SystemRole



## ======================================
## Helpers


def user_has_role(user, role, domain_obj):
    objectrole = UserObjectRole.get_object_role_class(domain_obj)
    return objectrole.user_has_role(user, role, domain_obj)

def add_user_to_role(user, role, domain_obj):
    objectrole = UserObjectRole.get_object_role_class(domain_obj)
    objectrole.add_user_to_role(user, role, domain_obj)

def remove_user_from_role(user, role, domain_obj):
    objectrole = UserObjectRole.get_object_role_class(domain_obj)
    objectrole.remove_user_from_role(user, role, domain_obj)


def init_authz_configuration_data():
    setup_default_user_roles(core.System())
    meta.Session.commit()
    meta.Session.remove()

def init_authz_const_data():
    '''Setup all default role-actions.

    These should be the same for all CKAN instances. Make custom roles if
    you want to divert from these.

    Note that Role.ADMIN can already do anything - hardcoded in.

    '''
    for role, action in default_role_actions:
        ra = meta.Session.query(RoleAction).filter_by(role=role, action=action).first()
        if ra is not None: continue
        ra = RoleAction(role=role, context=u'', action=action)
        meta.Session.add(ra)
    meta.Session.commit()
    meta.Session.remove()

## TODO: this should be removed
def setup_user_roles(_domain_object, visitor_roles, logged_in_roles, admins=[]):
    '''NB: leaves caller to commit change'''
    assert type(admins) == type([])
    admin_roles = [Role.ADMIN]
    visitor = _user.User.by_name(PSEUDO_USER__VISITOR)
    assert visitor
    for role in visitor_roles:
        add_user_to_role(visitor, role, _domain_object)
    logged_in = _user.User.by_name(PSEUDO_USER__LOGGED_IN)
    assert logged_in
    for role in logged_in_roles:
        add_user_to_role(logged_in, role, _domain_object)
    for admin in admins:
        # not sure if admin would reasonably by None
        if admin is not None:
            assert isinstance(admin, _user.User), admin
            if admin.name in (PSEUDO_USER__LOGGED_IN, PSEUDO_USER__VISITOR):
                raise NotRealUserException('Invalid user for domain object admin %r' % admin.name)
            for role in admin_roles:
                add_user_to_role(admin, role, _domain_object)

def give_all_packages_default_user_roles():
    # if this command gives an exception, you probably
    # forgot to do 'paster db init'
    pkgs = meta.Session.query(_package.Package).all()

    for pkg in pkgs:
        print pkg
        # weird - should already be in session but complains w/o this
        meta.Session.add(pkg)
        if len(pkg.roles) > 0:
            print 'Skipping (already has roles): %s' % pkg.name
            continue
        # work out the authors and make them admins
        admins = []
        revs = pkg.all_revisions
        for rev in revs:
            if rev.revision.author:
                # rev author is not Unicode!!
                user = _user.User.by_name(unicode(rev.revision.author))
                if user:
                    admins.append(user)
        # remove duplicates
        admins = list(set(admins))
        # gives default permissions
        print 'Creating default user for for %s with admins %s' % (pkg.name, admins)
        setup_default_user_roles(pkg, admins)

# default user roles - used when the config doesn\'t specify them
default_default_user_roles = {
    'Package': {"visitor": ["reader"], "logged_in": ["reader"]},
    'Group': {"visitor": ["reader"], "logged_in": ["reader"]},
    'System': {"visitor": ["reader"], "logged_in": ["editor"]},
    }

global _default_user_roles_cache
_default_user_roles_cache = weakref.WeakKeyDictionary()

def get_default_user_roles(_domain_object):
    # TODO: Should this func go in lib rather than model now?
    def _get_default_user_roles(_domain_object):
        config_key = 'ckan.default_roles.%s' % obj_type
        user_roles_json = config.get(config_key)
        if user_roles_json is None:
            user_roles_str = default_default_user_roles[obj_type]
        else:
            user_roles_str = json.loads(user_roles_json) if user_roles_json else {}
        unknown_keys = set(user_roles_str.keys()) - set(('visitor', 'logged_in'))
        assert not unknown_keys, 'Auth config for %r has unknown key %r' % \
               (_domain_object, unknown_keys)
        user_roles_ = {}
        for user in ('visitor', 'logged_in'):
            roles_str = user_roles_str.get(user, [])
            user_roles_[user] = [getattr(Role, role_str.upper()) for role_str in roles_str]
        return user_roles_
    obj_type = _domain_object.__class__.__name__
    global _default_user_roles_cache
    if not _default_user_roles_cache.has_key(_domain_object):
        _default_user_roles_cache[_domain_object] = _get_default_user_roles(_domain_object)
    return _default_user_roles_cache[_domain_object]

def setup_default_user_roles(_domain_object, admins=[]):
    ''' sets up roles for visitor, logged-in user and any admins provided
    @param admins - a list of User objects
    NB: leaves caller to commit change.
    '''
    assert isinstance(_domain_object, (_package.Package, group.Group, core.System)), _domain_object
    assert isinstance(admins, list)
    user_roles_ = get_default_user_roles(_domain_object)
    setup_user_roles(_domain_object,
                     user_roles_['visitor'],
                     user_roles_['logged_in'],
                     admins)

def clear_user_roles(_domain_object):
    assert isinstance(_domain_object, domain_object.DomainObject)
    if isinstance(_domain_object, _package.Package):
        q = meta.Session.query(PackageRole).filter_by(package=_domain_object)
    elif isinstance(_domain_object, group.Group):
        q = meta.Session.query(GroupRole).filter_by(group=_domain_object)
    else:
        raise NotImplementedError()
    user_roles = q.all()
    for user_role in user_roles:
        meta.Session.delete(user_role)


## ======================================
## Mappers

meta.mapper(RoleAction, role_action_table)

meta.mapper(UserObjectRole, user_object_role_table,
    polymorphic_on=user_object_role_table.c.context,
    polymorphic_identity=u'user_object',
    properties={
        'user': orm.relation(_user.User,
            backref=orm.backref('roles',
                cascade='all, delete, delete-orphan'
            )
        )
    },
    order_by=[user_object_role_table.c.id],
)

meta.mapper(PackageRole, package_role_table, inherits=UserObjectRole,
    polymorphic_identity=unicode(_package.Package.__name__),
    properties={
        'package': orm.relation(_package.Package,
             backref=orm.backref('roles',
             cascade='all, delete, delete-orphan'
             )
        ),
    },
    order_by=[package_role_table.c.user_object_role_id],
)

meta.mapper(GroupRole, group_role_table, inherits=UserObjectRole,
       polymorphic_identity=unicode(group.Group.__name__),
       properties={
            'group': orm.relation(group.Group,
                 backref=orm.backref('roles',
                 cascade='all, delete, delete-orphan'
                 ),
            )
    },
    order_by=[group_role_table.c.user_object_role_id],
)

meta.mapper(SystemRole, system_role_table, inherits=UserObjectRole,
       polymorphic_identity=unicode(core.System.__name__),
       order_by=[system_role_table.c.user_object_role_id],
)
