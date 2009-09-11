from meta import *
from core import Package, DomainObject
from types import make_uuid
from user import User

PSEUDO_USER__LOGGED_IN = u'logged_in'
PSEUDO_USER__VISITOR = u'visitor'

class Enum(object):
    @classmethod
    def is_valid(self, val):
        return val is not None and val in self.__dict__.values()

class Action(Enum):
    EDIT = u'edit'
    DELETE = u'delete'
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
           Column('package_id', Integer, ForeignKey('package.id')),
           )

class RoleAction(DomainObject):
    pass

class UserObjectRole(DomainObject):
    pass

class PackageRole(UserObjectRole):
    pass

mapper(RoleAction, role_action_table)
       
mapper(UserObjectRole, user_object_role_table,
       polymorphic_on=user_object_role_table.c.context,
       polymorphic_identity=u'user_object',
       properties={
        'user': orm.relation(User,
                 backref=orm.backref('roles',
                 cascade='all, delete'
                 ),
             )
    },
       order_by=[user_object_role_table.c.id],
)

mapper(PackageRole, package_role_table, inherits=UserObjectRole,
       polymorphic_identity=unicode(Package.__class__.__name__),
       properties={
            'package': orm.relation(Package,
                                    )
    },
    order_by=[package_role_table.c.user_object_role_id],
)

class NotRealUserException(Exception):
    pass

def setup_default_role_actions():
    visitor = User(name=PSEUDO_USER__VISITOR)
    logged_in = User(name=PSEUDO_USER__LOGGED_IN)
    
    # setup all role-actions (set context to None)

    # Note that Role.ADMIN can already do anything - hardcoded in.
    default_role_actions = [
        (Role.EDITOR, Action.EDIT),
        (Role.EDITOR, Action.CREATE),
        (Role.EDITOR, Action.READ),        
        (Role.READER, Action.CREATE),
        (Role.READER, Action.READ),
        ]
    for role, action in default_role_actions:
        ra = RoleAction(role=role,
                        context='', # Blank until used
                        action=action,
                        )

def add_user_to_role(user, role, domain_obj):
    assert isinstance(user, User), user
    assert user.id
    assert Role.is_valid(role), role
    assert isinstance(domain_obj, Package), domain_obj
    assert domain_obj.id

    if isinstance(domain_obj, Package):
        pr = PackageRole(role=role,
                         package=domain_obj,
                         user=user)
    else:
        raise NotImplementedError()

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
        assert isinstance(admin, User), admin
        if admin.name in (PSEUDO_USER__LOGGED_IN, PSEUDO_USER__VISITOR):
            raise NotRealUserException('Invalid user for domain object admin %r' % admin.name)
        for role in admin_roles:
            add_user_to_role(admin, role, domain_object)

def setup_default_user_roles(domain_object, admins=[]):
    # sets up visitor and logged-in user and admins if provided
    assert isinstance(domain_object, DomainObject)
    assert type(admins) == type([])
    visitor_roles = [Role.EDITOR, Role.READER]
    logged_in_roles = [Role.EDITOR, Role.READER]
    setup_user_roles(domain_object, visitor_roles, logged_in_roles, admins)

def clear_user_roles(domain_object):
    assert isinstance(domain_object, DomainObject)
    if isinstance(domain_object, Package):
        q = PackageRole.query.filter_by(package_id=domain_object.id)
    else:
        raise NotImplementedError()
    user_roles = q.all()
    for user_role in user_roles:
        Session.delete(user_role)
