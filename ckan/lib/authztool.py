
from ckan import model
from cli import CkanCommand

RIGHTS_HELP = '''

Operations (defaults to 'list'):
  rights list |grep ...
  rights make [subject] [role] [object]
  rights remove [subject] [role] [object]

Subjects (prefix defaults to 'user:'):
  user:fluffy87     - A user called 'fluffy87'
  agroup:editors    - An authorization group called 'editors'
  visitor           - All web site visitors
  logged_in         - All users that are logged in
  
Roles:
  %(roles)s
  
Objects (prefix defaults to 'package:'):
  package:datablob  - A package called 'datablob'
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
        
    def find_object(self, obj):
        _type, name = 'package', obj
        if obj == 'system':
            _type = 'system'
        elif ':' in obj:
            _type, name = obj.split(':', 1)
        finder = {
            'package': model.Package.by_name,
            'group': model.Group.by_name,
            'agroup': model.AuthorizationGroup.by_name,
            'system': model.System.by_name
        }.get(_type)
        assert finder is not None, "No subject object type: %s" % _type
        objn = finder(name)
        assert objn is not None, "No such %s: %s" % (_type, name)
        return objn
        
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
            self.list()
            return
        
        assert len(self.args) == 4, "Not enough paramters!" + RIGHTS_HELP
        cmd, subj, role, obj = self.args
        subj = self.find_subject(unicode(subj))
        role = self.ensure_role(unicode(role))
        obj = self.find_object(unicode(obj))
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
        model.repo.commit_and_remove()
        self.print_row(subj, role, obj)

    def list(self):
        for uor in model.Session.query(model.UserObjectRole):
            obj = getattr(uor, uor.name) if uor.name else model.System()
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
    