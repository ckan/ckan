
from ckan import model
from cli import CkanCommand

from sqlalchemy.orm.exc import NoResultFound

RIGHTS_HELP = '''

Operations (defaults to 'list'):
  rights list [[[<subject/object/role>] <subject/object/role>] ... ]
  rights make <subject> <role> <object>
  rights remove <subject> <role> <object>

Subjects (prefix defaults to 'user:'):
  user:fluffy87     - A user called 'fluffy87'
  agroup:editors    - An authorization group called 'editors'
  visitor           - All web site visitors
  logged_in         - All users that are logged in
  
Roles:
  %(roles)s
  
Objects (prefix defaults to 'package:'):
  package:datablob  - A package called 'datablob'
  package:all       - All packages
  group:literature  - A package group called 'literature'
  agroup:editors    - An authorization group called 'editors'
  system:           - The entire system (relevant to entity creation)
''' % dict(roles=", ".join(model.Role.get_all()))


class RightsCommand(CkanCommand):
    '''Commands relating to per-object and system-wide access rights.'''

    summary = __doc__.split('\n')[0]
    usage = RIGHTS_HELP
    max_args = 4
    min_args = 0
        
    def find_subject(self, subject):
        _type, name = 'user', subject
        if ':' in subject and not subject.lower().startswith('http'):
            _type, name = subject.split(':', 1)
        finder = {'agroup': model.AuthorizationGroup.by_name,
                  'user': model.User.by_name}.get(_type)
        assert finder is not None, "No such subject type: %s" % _type
        subj = finder(name)
        assert subj is not None, "No such %s: %s" % (_type, name)
        return subj
        
    def find_objects(self, obj):
        _type, name = 'package', obj
        if obj == 'system':
            _type = 'system'
        elif ':' in obj:
            _type, name = obj.split(':', 1)
        obj_class = {
            'package': model.Package,
            'group': model.Group,
            'agroup': model.AuthorizationGroup,
            'system': model.System,
        }.get(_type)
        if name == 'all':
            objn = model.Session.query(obj_class).all()
            return objn
        else:
            finder = obj_class.by_name
            assert finder is not None, "No subject object type: %s" % _type
            objn = finder(name)
            assert objn is not None, "No such %s: %s" % (_type, name)
            return [objn]
        
    def ensure_role(self, role):
        roles = model.Role.get_all()
        assert role in roles, "Role %s does not exist: %s" % (role, 
            ", ".join(roles))
        return role
        
    def print_row(self, subj, role, obj):
        #print "%-20s %-20s -> %-8s -> %-20s %s" % (type(subj).__name__, 
        print "%s %s -> is %s on -> %s %s" % (type(subj).__name__, 
            subj.name, role, type(obj).__name__, obj.name)

    def command(self):
        self._load_config()
        cmd = self.args[0] if len(self.args) else 'list'
        if cmd == 'list':
            args = self.args
            if 'list' in args:
                del args[args.index('list')]
            self.list(args)
            return
        
        assert len(self.args) == 4, "Not enough parameters!" + RIGHTS_HELP
        cmd, subj, role, obj = self.args
        subj = self.find_subject(unicode(subj))
        role = self.ensure_role(unicode(role))
        objs = self.find_objects(unicode(obj))
        for obj in objs:
            try:
                if cmd == 'make':
                    if isinstance(subj, model.User):
                        model.add_user_to_role(subj, role, obj)
                    elif isinstance(subj, model.AuthorizationGroup):
                        model.add_authorization_group_to_role(subj, role, obj)
                    print "made", 
                elif cmd == 'remove':
                    if isinstance(subj, model.User):
                        model.remove_user_from_role(subj, role, obj)
                    elif isinstance(subj, model.AuthorizationGroup):
                        model.remove_authorization_group_from_role(subj, role, obj)
                    print "remove",
            except NoResultFound, e:
                print "! not found",
            self.print_row(subj, role, obj)
        model.repo.commit_and_remove()

    def _filter_query(self, query, args):
        for arg in self.args:
            arg = unicode(arg)
            for interpret_func, column_name in ((self.ensure_role, 'role'),
                                                (self.find_subject, 'user'),
                                                (self.find_objects, 'object')):
                try:
                    filter_by_obj = interpret_func(arg)
                except AssertionError:
                    continue
                assert filter_by_obj, 'Could not interpret parameter: %r' % arg
                if column_name == 'user':
                    if isinstance(filter_by_obj, model.User):
                        column_name = 'user'
                    elif isinstance(filter_by_obj, model.AuthorizationGroup):
                        column_name = 'authorized_group'
                    else:
                        raise NotImplementedError
                if column_name == 'object':
                    if isinstance(filter_by_obj, list):
                        assert len(filter_by_obj) == 1, 'Can only filter by one object: %r' % arg
                        filter_by_obj = filter_by_obj[0]
                    protected_object = model.protected_objects[filter_by_obj.__class__]
                    column_name = protected_object.name
                    query = query.join(protected_object)
                    if column_name:
                        column = getattr(protected_object, column_name)
                    else:
                        # this is the case for SystemRole
                        # (just joining with the protected object is enough)
                        column = None
                else:
                    column = getattr(model.UserObjectRole, column_name)
                if column:
                    query = query.filter(column==filter_by_obj)
                break
            else:
                assert False, 'Could not find matching subject/object/role: %r' % arg
        return query

    def list(self, args):
        q = model.Session.query(model.UserObjectRole)
        q = self._filter_query(q, args)
        if q.count() == 0:
            print 'No results'
        else:
            print '%i results' % q.count()
        for uor in q:
            if uor.name:
                obj = getattr(uor, uor.name)
            else:
                obj = model.System()
            self.print_row(uor.user if uor.user else uor.authorized_group,
                           uor.role, obj)


ROLES_HELP = '''

Operations (defaults to 'list'):
 roles list
 roles allow [role] [action]
 roles deny [role] [action]

Actions:
 %(actions)s
''' % dict(actions=", ".join(model.Action.get_all()))

class RolesCommand(CkanCommand):
    '''Commands relating to roles and actions.'''

    summary = __doc__.split('\n')[0]
    usage = ROLES_HELP
    max_args = 3
    min_args = 0
    
    def command(self):
        self._load_config()
        cmd = self.args[0] if len(self.args) else 'list'
        if cmd == 'list':
            role_actions = model.Session.query(model.RoleAction)
            roles = {}
            for role_action in role_actions:
                roles[role_action.role] = \
                    roles.get(role_action.role, []) + [role_action.action]
            for role, actions in roles.items():
                print "%-20s%s" % (role, ", ".join(actions))
            return
        
        assert len(self.args) == 3, "Not enough paramters!" + ROLES_HELP
        cmd, role, action = self.args
        q = model.Session.query(model.RoleAction)
        q = q.filter(model.RoleAction.role==role)
        q = q.filter(model.RoleAction.action==action)
        role_action = q.first()
        if cmd == 'allow':
            assert not role_action, "%s can already %s." % (role, action)
            role_action = model.RoleAction(role=role, action=action, context=u'')
            model.Session.add(role_action)
        elif cmd == 'deny':
            assert role_action, "%s can't %s." % (role, action)
            model.Session.delete(role_action)
        model.repo.commit_and_remove()
    
