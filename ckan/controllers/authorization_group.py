import genshi

from sqlalchemy.orm import eagerload_all
from ckan.lib.base import *
import ckan.authz as authz
import ckan.forms
from ckan.lib.helpers import Page

class AuthorizationGroupController(BaseController):
    
    def __init__(self):
        BaseController.__init__(self)
        self.authorizer = authz.Authorizer()
    
    def index(self):
        from ckan.lib.helpers import Page

        query = ckan.authz.Authorizer().authorized_query(c.user, model.AuthorizationGroup)
        query = query.options(eagerload_all('users'))
        c.page = Page(
            collection=query,
            page=request.params.get('page', 1),
            items_per_page=20
        )
        return render('authorization_group/index.html')

    def read(self, id):
        c.authorization_group = model.AuthorizationGroup.by_name(id)
        if c.authorization_group is None:
            abort(404)
        auth_for_read = self.authorizer.am_authorized(c, model.Action.READ, 
                                                      c.authorization_group)
        if not auth_for_read:
            abort(401, gettext('Not authorized to read %s') % id.encode('utf8'))
        
        import ckan.misc
        c.authorization_group_admins = self.authorizer.get_admins(c.authorization_group)

        c.page = Page(
            collection=c.authorization_group.users,
            page=request.params.get('page', 1),
            items_per_page=50
        )
        return render('authorization_group/read.html')

    def new(self):
        record = model.AuthorizationGroup
        c.error = ''
        
        auth_for_create = self.authorizer.am_authorized(c, model.Action.AUTHZ_GROUP_CREATE, model.System())
        if not auth_for_create:
            abort(401, str(gettext('Unauthorized to create a group')))
        
        is_admin = self.authorizer.is_sysadmin(c.user)
        
        fs = ckan.forms.get_authorization_group_fieldset(is_admin=is_admin)

        if request.params.has_key('save'):
            # needed because request is nested
            # multidict which is read only
            params = dict(request.params)
            c.fs = fs.bind(record, data=params or None, session=model.Session)
            try:
                self._update(c.fs, id, record.id)
            except ValidationException, error:
                fs = error.args[0]
                c.form = self._render_edit_form(fs)
                return render('authorization_group/edit.html')
            # do not use groupname from id as may have changed
            c.authzgroupname = c.fs.name.value
            authorization_group = model.AuthorizationGroup.by_name(c.authzgroupname)
            assert authorization_group
            user = model.User.by_name(c.user)
            model.setup_default_user_roles(authorization_group, [user])
            users = [model.User.by_name(name) for name in \
                     request.params.getall('AuthorizationGroup-users-current')]
            authorization_group.users = list(set(users + [user]))
            usernames = request.params.getall('AuthorizationGroupUser--user_name')
            for username in usernames:
                if username:
                    usr = model.User.by_name(username)
                    if usr and usr not in authorization_group.users:
                        model.add_user_to_authorization_group(usr, authorization_group, model.Role.READER)
            model.repo.commit_and_remove()
            h.redirect_to(action='read', id=c.authzgroupname)

        if request.params:
            data = ckan.forms.edit_group_dict(ckan.forms.get_authorization_group_dict(), request.params)
            fs = fs.bind(data=data, session=model.Session)
        c.form = self._render_edit_form(fs)
        return render('authorization_group/new.html')

    def edit(self, id=None): # allow id=None to allow posting
        c.error = ''
        authorization_group = model.AuthorizationGroup.by_name(id)
        if authorization_group is None:
            abort(404, '404 Not Found')
        am_authz = self.authorizer.am_authorized(c, model.Action.EDIT, authorization_group)
        if not am_authz:
            abort(401, gettext('User %r not authorized to edit %r') % (c.user, id))
            
        is_admin = self.authorizer.is_sysadmin(c.user)
        
        if not 'save' in request.params:
            c.authorization_group = authorization_group
            c.authorization_group_name = authorization_group.name
            
            fs = ckan.forms.get_authorization_group_fieldset(is_admin=is_admin).bind(authorization_group)
            c.form = self._render_edit_form(fs)
            return render('authorization_group/edit.html')
        else:
            # id is the name (pre-edited state)
            c.authorization_group_name = id
            # needed because request is nested
            # multidict which is read only
            params = dict(request.params)
            c.fs = ckan.forms.get_authorization_group_fieldset()\
                .bind(authorization_group, data=params or None)
            try:
                self._update(c.fs, id, authorization_group.id)
                # do not use groupname from id as may have changed
                c.authorization_group = authorization_group
                c.authorization_group_name = authorization_group.name
            except ValidationException, error:
                fs = error.args[0]
                c.form = self._render_edit_form(fs)
                return render('authorization_group/edit.html')
            user = model.User.by_name(c.user)
            users = [model.User.by_name(name) for name in \
                     request.params.getall('AuthorizationGroup-users-current')]
            authorization_group.users = list(set(users + [user]))
            usernames = request.params.getall('AuthorizationGroupUser--user_name')
            for username in usernames:
                if username:
                    usr = model.User.by_name(username)
                    if usr and usr not in authorization_group.users:
                        model.add_user_to_authorization_group(usr, authorization_group, model.Role.READER)
            model.repo.commit_and_remove()
            h.redirect_to(action='read', id=c.authorization_group_name)

    def authz(self, id):
        c.authorization_group = model.AuthorizationGroup.by_name(id)
        if c.authorization_group is None:
            abort(404, gettext('Group not found'))
        c.authorization_group_name = c.authorization_group.name
        
        c.authz_editable = self.authorizer.am_authorized(c, model.Action.EDIT_PERMISSIONS, 
                                                         c.authorization_group)
        if not c.authz_editable:
            abort(401, gettext('Not authorized to edit authorization for group'))

        if 'save' in request.params: # form posted
            # needed because request is nested
            # multidict which is read only
            params = dict(request.params)
            c.fs = ckan.forms.get_authz_fieldset('authorization_group_authz_fs').bind(
                                                 c.authorization_group.roles, 
                                                 data=params or None)
            try:
                self._update_authz(c.fs)
            except ValidationException, error:
                # TODO: sort this out 
                # fs = error.args[0]
                # return render('group/authz.html')
                raise
            # now do new roles
            newrole_user_id = request.params.get('AuthorizationGroupRole--user_id')
            newrole_authzgroup_id = request.params.get('AuthorizationGroupRole--authorized_group_id')
            if newrole_user_id != '__null_value__' and newrole_authzgroup_id != '__null_value__':
                c.message = _(u'Please select either a user or an authorization group, not both.')
            elif newrole_user_id != '__null_value__':
                user = model.Session.query(model.User).get(newrole_user_id)
                # TODO: chech user is not None (should go in validation ...)
                role = request.params.get('AuthorizationGroupRole--role')
                newauthzgrouprole = model.AuthorizationGroupRole(user=user, 
                        authorization_group=c.authorization_group, role=role)
                # With FA no way to get new GroupRole back to set group attribute
                # new_roles = ckan.forms.new_roles_fs.bind(model.GroupRole, data=params or None)
                # new_roles.sync()
                model.Session.commit()
                model.Session.remove()
                c.message = _(u'Added role \'%s\' for user \'%s\'') % (
                    newauthzgrouprole.role,
                    newauthzgrouprole.user.name)      
            elif newrole_authzgroup_id != '__null_value__':
                authzgroup = model.Session.query(model.AuthorizationGroup).get(newrole_authzgroup_id)
                # TODO: chech user is not None (should go in validation ...)
                role = request.params.get('AuthorizationGroupRole--role')
                newauthzgrouprole = model.AuthorizationGroupRole(authorized_group=authzgroup, 
                        authorization_group=c.authorization_group, role=role)
                # With FA no way to get new GroupRole back to set group attribute
                # new_roles = ckan.forms.new_roles_fs.bind(model.GroupRole, data=params or None)
                # new_roles.sync()
                model.Session.commit()
                model.Session.remove()
                c.message = _(u'Added role \'%s\' for authorization group \'%s\'') % (
                    newauthzgrouprole.role,
                    newauthzgrouprole.authorized_group.name)
        elif 'role_to_delete' in request.params:
            authzgrouprole_id = request.params['role_to_delete']
            authzgrouprole = model.Session.query(model.AuthorizationGroupRole).get(authzgrouprole_id)
            if authzgrouprole is None:
                c.error = _(u'Error: No role found with that id')
            else:
                authzgrouprole.purge()
                if authzgrouprole.user:
                    c.message = _(u'Deleted role \'%s\' for user \'%s\'') % \
                                (authzgrouprole.role, authzgrouprole.user.name)
                elif authzgrouprole.authorized_group:
                    c.message = _(u'Deleted role \'%s\' for authorization group \'%s\'') % \
                                (authzgrouprole.role, authzgrouprole.authorized_group.name)
                model.Session.commit()

        # retrieve group again ...
        c.authorization_group = model.AuthorizationGroup.by_name(id)
        fs = ckan.forms.get_authz_fieldset('authorization_group_authz_fs')\
                .bind(c.authorization_group.roles)
        c.form = fs.render()
        c.new_roles_form = \
            ckan.forms.get_authz_fieldset('new_authorization_group_roles_fs').render()
        return render('authorization_group/authz.html')

    def _render_edit_form(self, fs):
        # errors arrive in c.error and fs.errors
        c.fieldset = fs
        c.fieldset2 = ckan.forms.get_authorization_group_user_fieldset()
        return render('authorization_group/edit_form.html')

    def _update(self, fs, group_name, group_id):
        '''
        Writes the POST data (associated with a group edit) to the database
        @input c.error
        '''
        validation = fs.validate()
        if not validation:
            c.form = self._render_edit_form(fs)
            raise ValidationException(fs)

        try:
            fs.sync()
        except Exception, inst:
            model.Session.rollback()
            raise
        else:
            model.Session.commit()

    def _update_authz(self, fs):
        validation = fs.validate()
        if not validation:
            c.form = self._render_edit_form(fs)
            raise ValidationException(fs)
        try:
            fs.sync()
        except Exception, inst:
            model.Session.rollback()
            raise
        else:
            model.Session.commit()
