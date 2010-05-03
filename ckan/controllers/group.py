import genshi

from ckan.lib.base import *
from simplejson import dumps
import ckan.authz as authz
import ckan.forms
from ckan.lib.helpers import Page

class GroupController(BaseController):
    def __init__(self):
        BaseController.__init__(self)
        self.authorizer = authz.Authorizer()
    
    def index(self):
        from ckan.lib.helpers import Page

        query = ckan.authz.Authorizer().authorized_query(c.user, model.Group)
        c.page = Page(
            collection=query,
            page=request.params.get('page', 1),
            items_per_page=20
        )
        return render('group/index')

    def read(self, id):
        c.group = model.Group.by_name(id)
        if c.group is None:
            abort(404)
        auth_for_read = self.authorizer.am_authorized(c, model.Action.READ, c.group)
        if not auth_for_read:
            abort(401, gettext('Not authorized to read %s') % id.encode('utf8'))

        c.auth_for_edit = self.authorizer.am_authorized(c, model.Action.EDIT, c.group)
        c.auth_for_authz = self.authorizer.am_authorized(c, model.Action.EDIT_PERMISSIONS, c.group)
        
        import ckan.misc
        format = ckan.misc.MarkdownFormat()
        desc_formatted = format.to_html(c.group.description)
        desc_formatted = genshi.HTML(desc_formatted)
        c.group_description_formatted = desc_formatted
        c.group_admins = self.authorizer.get_admins(c.group)

        c.page = Page(
            collection=c.group.active_packages(),
            page=request.params.get('page', 1),
            items_per_page=50
        )
        return render('group/read')

    def new(self):
        record = model.Group
        c.error = ''
        if not c.user:
            abort(401, gettext('Must be logged in to create a new group.'))

        fs = ckan.forms.get_group_fieldset('group_fs')

        if request.params.has_key('commit'):
            # needed because request is nested
            # multidict which is read only
            params = dict(request.params)
            c.fs = fs.bind(record, data=params or None, session=model.Session)
            try:
                self._update(c.fs, id, record.id)
            except ValidationException, error:
                fs = error.args[0]
                c.form = self._render_edit_form(fs)
                return render('group/edit')
            # do not use groupname from id as may have changed
            c.groupname = c.fs.name.value
            group = model.Group.by_name(c.groupname)
            assert group
            admins = []
            user = model.User.by_name(c.user)
            admins = [user]
            model.setup_default_user_roles(group, admins)
            group = model.Group.by_name(c.groupname)
            pkgs = [model.Package.by_name(name) for name in request.params.getall('Group-packages-current')]
            group.packages = pkgs
            pkgids = request.params.getall('PackageGroup--package_id')
            for pkgid in pkgids:
                if pkgid:
                    package = model.Session.query(model.Package).get(pkgid)
                    if package and package not in group.packages:
                        group.packages.append(package)
            model.repo.commit_and_remove()
            h.redirect_to(action='read', id=c.groupname)

        if request.params:
            data = ckan.forms.edit_group_dict(ckan.forms.get_group_dict(), request.params)
            fs = fs.bind(data=data, session=model.Session)
        c.form = self._render_edit_form(fs)
        return render('group/new')

    def edit(self, id=None): # allow id=None to allow posting
        c.error = ''
        group = model.Group.by_name(id)
        if group is None:
            abort(404, '404 Not Found')
        am_authz = self.authorizer.am_authorized(c, model.Action.EDIT, group)
        if not am_authz:
            abort(401, gettext('User %r not authorized to edit %r') % (c.user, id))

        if not 'commit' in request.params:
            c.group = group
            c.groupname = group.name
            
            fs = ckan.forms.get_group_fieldset('group_fs').bind(c.group)
            c.form = self._render_edit_form(fs)
            return render('group/edit')
        else:
            # id is the name (pre-edited state)
            c.groupname = id
            # needed because request is nested
            # multidict which is read only
            params = dict(request.params)
            c.fs = ckan.forms.get_group_fieldset('group_fs').bind(group, data=params or None)
            try:
                self._update(c.fs, id, group.id)
                # do not use groupname from id as may have changed
                c.groupname = c.fs.name.value
            except ValidationException, error:
                fs = error.args[0]
                c.form = self._render_edit_form(fs)
                return render('group/edit')
            pkgs = [model.Package.by_name(name) for name in request.params.getall('Group-packages-current')]
            group.packages = pkgs
            pkgids = request.params.getall('PackageGroup--package_id')
            for pkgid in pkgids:
                if pkgid:
                    package = model.Session.query(model.Package).get(pkgid)
                    if package and package not in group.packages:
                        group.packages.append(package)
            model.repo.commit_and_remove()
            h.redirect_to(action='read', id=c.groupname)

    def authz(self, id):
        group = model.Group.by_name(id)
        if group is None:
            abort(404, gettext('Group not found'))
        c.groupname = group.name

        c.authz_editable = self.authorizer.am_authorized(c, model.Action.EDIT_PERMISSIONS, group)
        if not c.authz_editable:
            abort(401, gettext('Not authorized to edit authization for group'))

        if 'commit' in request.params: # form posted
            # needed because request is nested
            # multidict which is read only
            params = dict(request.params)
            c.fs = ckan.forms.get_authz_fieldset('group_authz_fs').bind(group.roles, data=params or None)
            try:
                self._update_authz(c.fs)
            except ValidationException, error:
                # TODO: sort this out 
                # fs = error.args[0]
                # return render('group/authz')
                raise
            # now do new roles
            newrole_user_id = request.params.get('GroupRole--user_id')
            if newrole_user_id != '__null_value__':
                user = model.Session.query(model.User).get(newrole_user_id)
                # TODO: chech user is not None (should go in validation ...)
                role = request.params.get('GroupRole--role')
                newgrouprole = model.GroupRole(user=user, group=group,
                        role=role)
                # With FA no way to get new GroupRole back to set group attribute
                # new_roles = ckan.forms.new_roles_fs.bind(model.GroupRole, data=params or None)
                # new_roles.sync()
                model.Session.commit()
                model.Session.remove()
                c.message = _(u'Added role \'%s\' for user \'%s\'') % (
                    newgrouprole.role,
                    newgrouprole.user.name)
        elif 'role_to_delete' in request.params:
            grouprole_id = request.params['role_to_delete']
            grouprole = model.Session.query(model.GroupRole).get(grouprole_id)
            if grouprole is None:
                c.error = _(u'Error: No role found with that id')
            else:
                grouprole.purge()
                c.message = _(u'Deleted role \'%s\' for user \'%s\'') % \
                            (grouprole.role, grouprole.user.name)
                model.Session.commit()

        # retrieve group again ...
        group = model.Group.by_name(id)
        fs = ckan.forms.get_authz_fieldset('group_authz_fs').bind(group.roles)
        c.form = fs.render()
        c.new_roles_form = ckan.forms.get_authz_fieldset('new_group_roles_fs').render()
        return render('group/authz')

    def _render_edit_form(self, fs):
        # errors arrive in c.error and fs.errors
        c.fieldset = fs
        c.fieldset2 = ckan.forms.get_group_fieldset('new_package_group_fs')
        return render('group/edit_form')

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
