import logging

from sqlalchemy.orm.exc import NoResultFound, ObjectDeletedError

from cli import CkanCommand
# NB No CKAN imports allowed until in a command, or the logging does not work

class RightsToolError(Exception):
    pass

class RightsTool(object):
    # TODO: Consider moving this to logic layer
    @classmethod
    def make_or_remove_roles(cls, cmd, subj, role, obj, except_on_error=False, do_commit=True):
        '''Tool to make or remove a role using the names of objects, rather
        than the actual objects.
        cmd - 'make' or 'remove'
        subj - name of subject object (e.g. 'dave-admin')
        role - name of role (e.g. 'editor')
        obj - names of an objects to apply the role to (e.g. 'river-stats' or 'all')
        '''
        from ckan import model
        log = logging.getLogger(__name__)

        subj = cls.find_subject(unicode(subj))
        role = cls.ensure_role(unicode(role))
        objs = cls.find_objects(unicode(obj))
        for obj in objs:
            try:
                if cmd == 'make':
                    if isinstance(subj, model.User):
                        model.add_user_to_role(subj, role, obj)
                    elif isinstance(subj, model.AuthorizationGroup):
                        model.add_authorization_group_to_role(subj, role, obj)
                    log.debug('Role made')
                elif cmd == 'remove':
                    if isinstance(subj, model.User):
                        model.remove_user_from_role(subj, role, obj)
                    elif isinstance(subj, model.AuthorizationGroup):
                        model.remove_authorization_group_from_role(subj, role, obj)
                    log.debug('Role removed')
                else:
                    raise NotImplementedError
            except NoResultFound, e:
                log.error('Cannot find object for role %s: %s', str(e), cmd)
                if except_on_error:
                    raise RightsToolError('Cannot %s right: %s %s %s', cmd, subj, role, obj)
            log.debug(cls.get_printable_row(subj, role, obj,
                                            exists=(cmd=='make')))
        if do_commit:
            model.repo.commit_and_remove()
    
    @classmethod
    def find_subject(cls, subject):
        '''Given a name of a system object that could be the subject
        of a role, returns the object.'''
        from ckan import model
        _type, name = 'user', subject
        if ':' in subject and not subject.lower().startswith('http'):
            _type, name = subject.split(':', 1)
        finder = {'agroup': model.AuthorizationGroup.by_name,
                  'user': model.User.by_name}.get(_type)
        assert finder is not None, "No such subject type: %s" % _type
        subj = finder(name)
        assert subj is not None, "No such %s: %s" % (_type, name)
        return subj

    @classmethod
    def find_objects(cls, obj):
        '''Given a name of a system object, returns the object'''
        # NB: There is some overlap here with ckan.logic.action.get_domain_object
        from ckan import model
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

    @staticmethod
    def ensure_role(role):
        from ckan import model
        roles = model.Role.get_all()
        assert role in roles, "Role %s does not exist: %s" % (role, 
            ", ".join(roles))
        return role

    @staticmethod
    def get_printable_row(subj, role, obj, exists=True):
        return "%s %s -> %s %s on -> %s %s" % \
               (type(subj).__name__, subj.name,
                'is' if exists else 'is NOT', role,
                type(obj).__name__, obj.name)

class RightsCommand(CkanCommand):
    '''Commands relating to per-object and system-wide access rights.'''

    summary = __doc__.split('\n')[0]
    max_args = 4
    min_args = 0

    @property
    def usage(self):
        from ckan import model
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
        return RIGHTS_HELP
        

    def command(self):
        self._load_config()
        cmd = self.args[0] if len(self.args) else 'list'
        if cmd == 'list':
            args = self.args
            if 'list' in args:
                del args[args.index('list')]
            self.list(args)
            return
        assert len(self.args) == 4, "Not enough parameters!" + self.usage
        cmd, subj, role, obj = self.args

        RightsTool.make_or_remove_roles(cmd, subj, role, obj, except_on_error=False)

    def _filter_query(self, query, args):
        from ckan import model        
        for arg in self.args:
            arg = unicode(arg)
            for interpret_func, column_name in ((RightsTool.ensure_role, 'role'),
                                                (RightsTool.find_subject, 'user'),
                                                (RightsTool.find_objects, 'object')):
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
        from ckan import model
        q = model.Session.query(model.UserObjectRole)
        q = self._filter_query(q, args)
        if q.count() == 0:
            print 'No results'
        else:
            print '%i results' % q.count()
        for uor in q:
            if uor.name:
                try:
                    obj = getattr(uor, uor.name)
                except ObjectDeletedError, e:
                    print '! ERROR accessing uor id: ', uor.id
                    continue
            else:
                obj = model.System()
            print RightsTool.get_printable_row(
                uor.user if uor.user else uor.authorized_group,
                uor.role, obj)



class RolesCommand(CkanCommand):
    '''Commands relating to roles and actions.'''

    summary = __doc__.split('\n')[0]
    max_args = 3
    min_args = 0

    @property
    def usage(self):
        from ckan import model
        ROLES_HELP = '''
Operations (defaults to 'list'):
 roles list
 roles allow [role] [action]
 roles deny [role] [action]

Actions:
 %(actions)s
''' % dict(actions=", ".join(model.Action.get_all()))
        return ROLES_HELP
    
    def command(self):
        from ckan import model
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
        
        assert len(self.args) == 3, "Not enough paramters!" + self.usage
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
        print 'Successful: %s %s %s' % (cmd, role, action)
        model.repo.commit_and_remove()
    
