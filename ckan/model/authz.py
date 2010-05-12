from meta import *
from core import DomainObject, Package, System
from group import Group
from types import make_uuid
from user import User

PSEUDO_USER__LOGGED_IN = u'logged_in'
PSEUDO_USER__VISITOR = u'visitor'

class Enum(object):
    @classmethod
    def is_valid(self, val):
        return val in self.get_all()

    @classmethod
    def get_all(self):
        if not hasattr(self, '_all_items'):
            vals = []
            for key, val in self.__dict__.items():
                if not key.startswith('_'):
                    vals.append(val)
            self._all_items = vals
        return self._all_items

class Action(Enum):
    EDIT = u'edit'
    CHANGE_STATE = u'change-state'
    READ = u'read'
    PURGE = u'purge'
    EDIT_PERMISSIONS = u'edit-permissions'
    CREATE = u'create'

class Role(Enum):
    ADMIN = u'admin'
    EDITOR = u'editor'
    READER = u'reader'

role_action_table = Table('role_action', metadata,
           Column('id', UnicodeText, primary_key=True, default=make_uuid),
           Column('role', UnicodeText),
           Column('context', UnicodeText, nullable=False),
           Column('action', UnicodeText),
           )

user_object_role_table = Table('user_object_role', metadata,
           Column('id', UnicodeText, primary_key=True, default=make_uuid),
           Column('user_id', UnicodeText, ForeignKey('user.id')),
           Column('context', UnicodeText, nullable=False),
           Column('role', UnicodeText)
           )

package_role_table = Table('package_role', metadata,
           Column('user_object_role_id', UnicodeText, ForeignKey('user_object_role.id'), primary_key=True),
           Column('package_id', UnicodeText, ForeignKey('package.id')),
           )

group_role_table = Table('group_role', metadata,
           Column('user_object_role_id', UnicodeText, ForeignKey('user_object_role.id'), primary_key=True),
           Column('group_id', UnicodeText, ForeignKey('group.id')),
           )

system_role_table = Table('system_role', metadata,
           Column('user_object_role_id', UnicodeText, ForeignKey('user_object_role.id'), primary_key=True),
           )

class RoleAction(DomainObject):
    pass

class UserObjectRole(DomainObject):
    pass

class PackageRole(UserObjectRole):
    pass

class GroupRole(UserObjectRole):
    pass

class SystemRole(UserObjectRole):
    pass

mapper(RoleAction, role_action_table)
       
mapper(UserObjectRole, user_object_role_table,
    polymorphic_on=user_object_role_table.c.context,
    polymorphic_identity=u'user_object',
    properties={
        'user': orm.relation(User,
            backref=orm.backref('roles',
                cascade='all, delete, delete-orphan'
            )
        )
    },
    order_by=[user_object_role_table.c.id],
)

mapper(PackageRole, package_role_table, inherits=UserObjectRole,
    polymorphic_identity=unicode(Package.__name__),
    properties={
        'package': orm.relation(Package,
             backref=orm.backref('roles',
             cascade='all, delete, delete-orphan'
             )
        ),
    },
    order_by=[package_role_table.c.user_object_role_id],
)

mapper(GroupRole, group_role_table, inherits=UserObjectRole,
       polymorphic_identity=unicode(Group.__name__),
       properties={
            'group': orm.relation(Group,
                 backref=orm.backref('roles',
                 cascade='all, delete, delete-orphan'
                 ),
            )
    },
    order_by=[group_role_table.c.user_object_role_id],
)

mapper(SystemRole, system_role_table, inherits=UserObjectRole,
       polymorphic_identity=unicode(System.__name__),
       order_by=[system_role_table.c.user_object_role_id],
)

class NotRealUserException(Exception):
    pass

default_role_actions = [
    (Role.EDITOR, Action.EDIT),
    (Role.EDITOR, Action.CREATE),
    (Role.EDITOR, Action.READ),        
    (Role.READER, Action.CREATE),
    (Role.READER, Action.READ),
    ]

def user_has_role(user, role, domain_obj):
    assert isinstance(user, User), user
    assert user.id
    assert Role.is_valid(role), role
    assert isinstance(domain_obj, (Package, Group, System)), domain_obj
    assert domain_obj.id
    
    if isinstance(domain_obj, Package):
        return Session.query(PackageRole).filter_by(role=role,
                                           package=domain_obj,
                                           user=user).count() == 1
    elif isinstance(domain_obj, Group):
        return Session.query(GroupRole).filter_by(role=role,
                                           group=domain_obj,
                                           user=user).count() == 1
    elif isinstance(domain_obj, System):
        return Session.query(SystemRole).filter_by(role=role,
                                          user=user).count() == 1
    else:
        raise NotImplementedError()


def add_user_to_role(user, role, domain_obj):
    assert Role.is_valid(role), role

    if isinstance(domain_obj, Package):
        existing_pr = Session.query(PackageRole).filter_by(role=role,
                                                  package=domain_obj,
                                                  user=user).count()
    elif isinstance(domain_obj, Group):        
        existing_pr = Session.query(GroupRole).filter_by(role=role,
                                                group=domain_obj,
                                                user=user).count()
    elif isinstance(domain_obj, System):        
        existing_pr = Session.query(SystemRole).filter_by(role=role,
                                                 user=user).count()
    else:
        msg = '%s is not an object for which there are roles' % domain_obj
        raise NotImplementedError(msg)
    if existing_pr:
        return

    if isinstance(domain_obj, Package):
        pr = PackageRole(role=role,
                         package=domain_obj,
                         user=user)
    elif isinstance(domain_obj, Group):
        pr = GroupRole(role=role,
                         group=domain_obj,
                         user=user)
    elif isinstance(domain_obj, System):
        pr = SystemRole(role=role,
                        user=user)
    else:
        raise NotImplementedError()
    Session.add(pr)

def remove_user_from_role(user, role, domain_obj):
    '''NB This calls Session.commit()'''
    assert Role.is_valid(role), role

    if isinstance(domain_obj, Package):
        uo_role = Session.query(PackageRole).filter_by(role=role,
                                         package=domain_obj,
                                         user=user).one()
    elif isinstance(domain_obj, Group):
        uo_role = Session.query(GroupRole).filter_by(role=role,
                                         group=domain_obj,
                                         user=user).one()
    elif isinstance(domain_obj, System):
        uo_role = Session.query(SystemRole).filter_by(role=role,
                                         user=user).one()
    else:
        raise NotImplementedError()

    Session.delete(ou_role)

    Session.commit()
    Session.remove()

def setup_user_roles(domain_object, visitor_roles, logged_in_roles, admins=[]):
    assert type(admins) == type([])
    admin_roles = [Role.ADMIN]
    visitor = User.by_name(PSEUDO_USER__VISITOR)
    for role in visitor_roles:
        add_user_to_role(visitor, role, domain_object)
    logged_in = User.by_name(PSEUDO_USER__LOGGED_IN)
    for role in logged_in_roles:
        add_user_to_role(logged_in, role, domain_object)
    for admin in admins:
        # not sure if admin would reasonably by None
        if admin is not None:
            assert isinstance(admin, User), admin
            if admin.name in (PSEUDO_USER__LOGGED_IN, PSEUDO_USER__VISITOR):
                raise NotRealUserException('Invalid user for domain object admin %r' % admin.name)
            for role in admin_roles:
                add_user_to_role(admin, role, domain_object)

def give_all_packages_default_user_roles():
    # if this command gives an exception, you probably
    # forgot to do 'paster db init'
    pkgs = Session.query(Package).all()

    for pkg in pkgs:
        print pkg
        # weird - should already be in session but complains w/o this
        Session.add(pkg)
        if len(pkg.roles) > 0:
            print 'Skipping (already has roles): %s' % pkg.name
            continue
        # work out the authors and make them admins
        admins = []
        revs = pkg.all_revisions
        for rev in revs:
            if rev.revision.author:
                # rev author is not Unicode!!
                user = User.by_name(unicode(rev.revision.author))
                if user:
                    admins.append(user)
        # remove duplicates
        admins = list(set(admins))
        # gives default permissions
        print 'Creating default user for for %s with admins %s' % (pkg.name, admins)
        setup_default_user_roles(pkg, admins)

def setup_default_user_roles(domain_object, admins=[]):
    # sets up roles for visitor, logged-in user and any admins provided
    # admins is a list of User objects
    assert isinstance(domain_object, (Package, Group))
    assert isinstance(admins, list)
    if type(domain_object) == Package:
        visitor_roles = [Role.EDITOR]
        logged_in_roles = [Role.EDITOR]
    elif type(domain_object) == Group:
        visitor_roles = [Role.READER]
        logged_in_roles = [Role.READER]
    setup_user_roles(domain_object, visitor_roles, logged_in_roles, admins)

def clear_user_roles(domain_object):
    assert isinstance(domain_object, DomainObject)
    if isinstance(domain_object, Package):
        q = Session.query(PackageRole).filter_by(package=domain_object)
    elif isinstance(domain_object, Group):
        q = Session.query(GroupRole).filter_by(group=domain_object)
    else:
        raise NotImplementedError()
    user_roles = q.all()
    for user_role in user_roles:
        Session.delete(user_role)
