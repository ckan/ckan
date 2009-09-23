import genshi

from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController, ValidationException
from simplejson import dumps
import ckan.authz as authz
import ckan.forms

class GroupController(CkanBaseController):
    def __init__(self):
        CkanBaseController.__init__(self)
        self.authorizer = authz.Authorizer()
    
    def index(self):
        return self.list()

    def list(self, id=0):
        return self._paginate_list('group', id, 'group/list', ['name', 'title'])

    def read(self, id):
        c.group = model.Group.by_name(id)
        if c.group is None:
            abort(404)
        c.auth_for_edit = self.authorizer.am_authorized(c, model.Action.EDIT, c.group)
        c.auth_for_authz = self.authorizer.am_authorized(c, model.Action.EDIT_PERMISSIONS, c.group)
        
        fs = ckan.forms.group_fs.bind(c.group)
        c.content = genshi.HTML(self._render_group(fs))

        return render('group/read')

    def autocomplete(self):
        incomplete = request.params.get('incomplete', '')
        if incomplete:
            groups = list(model.Group.search_by_name(incomplete))
            groupNames = [t.name for t in groups]
        else:
            groupNames = []
        resultSet = {
            "ResultSet": {
                "Result": []
            }
        }
        for groupName in groupNames[:10]:
            result = {
                "Name": groupName
            }
            resultSet["ResultSet"]["Result"].append(result)
        return dumps(resultSet)

    def edit(self, id=None): # allow id=None to allow posting
        c.error = ''
        group = model.Group.by_name(id)
        if group is None:
            abort(404, '404 Not Found')
        am_authz = self.authorizer.am_authorized(c, model.Action.EDIT, group)
        if not am_authz:
            abort(401, 'User %r unauthorized to edit %r' % (c.user, id))

        if not 'commit' in request.params in request.params:
            # edit
            c.group = group
            c.groupname = group.name
            
            fs = ckan.forms.group_fs.bind(c.group)
            c.form = self._render_edit_form(fs)
            return render('group/edit')
        else:
            # id is the name (pre-edited state)
            c.groupname = id
            params = dict(request.params) # needed because request is nested
                                          # multidict which is read only
            c.fs = ckan.forms.group_fs.bind(group, data=params or None)
            try:
                self._update(c.fs, id, group.id)
                # do not use groupname from id as may have changed
                c.groupname = c.fs.name.value
                h.redirect_to(action='read', id=c.groupname)
            except ValidationException, error:
                c.error, fs = error.args
                c.form = self._render_edit_form(fs)
                return render('group/edit')

    def authz(self, id):
        group = model.Group.by_name(id)
        if group is None:
            abort(404, '404 Not Found')
        c.groupname = group.name

        c.authz_editable = self.authorizer.am_authorized(c, model.Action.EDIT_PERMISSIONS, group)
        if not c.authz_editable:
            abort(401, '401 Access denied')                

        if 'commit' in request.params: # form posted
            # needed because request is nested
            # multidict which is read only
            params = dict(request.params)
            c.fs = ckan.forms.group_authz_fs.bind(group.roles, data=params or None)
            try:
                self._update_authz(c.fs)
            except ValidationException, error:
                # TODO: sort this out 
                # c.error, fs = error.args
                # return render('group/authz')
                raise
            # now do new roles
            newrole_user_id = request.params.get('GroupRole--user_id')
            if newrole_user_id != '__null_value__':
                user = model.User.query.get(newrole_user_id)
                # TODO: chech user is not None (should go in validation ...)
                role = request.params.get('GroupRole--role')
                newgrouprole = model.GroupRole(user=user, group=group,
                        role=role)
                # With FA no way to get new GroupRole back to set group attribute
                # new_roles = ckan.forms.new_roles_fs.bind(model.GroupRole, data=params or None)
                # new_roles.sync()
                model.Session.commit()
                model.Session.remove()
        elif 'role_to_delete' in request.params:
            grouprole_id = request.params['role_to_delete']
            grouprole = model.GroupRole.query.get(grouprole_id)
            if grouprole is None:
                c.message = 'Error: No role found with that id'
            else:
                grouprole.purge()
                model.Session.commit()
                c.message = u'Deleted role %s for user %s' % (grouprole.role,
                        grouprole.user)

        # retrieve group again ...
        group = model.Group.by_name(id)
        fs = ckan.forms.group_authz_fs.bind(group.roles)
        c.form = fs.render()
        c.new_roles_form = ckan.forms.new_group_roles_fs.render()
        return render('group/authz')

    def _render_edit_form(self, fs):
        # errors arrive in c.error and fs.errors
        c.form = fs.render()
        return render('group/edit_form')

    def _render_group(self, fs):
        # note: doesn't render package list
        c.group_name = fs.name.value
        c.group_title = fs.title.value
        import ckan.misc
        format = ckan.misc.MarkdownFormat()
        desc_formatted = format.to_html(fs.description.value)
        desc_formatted = genshi.HTML(desc_formatted)
        c.group_description_formatted = desc_formatted
        preview = render('group/read_content')
        return preview

    def _update(self, fs, group_name, group_id):
        '''
        Writes the POST data (associated with a group edit) to the database
        @input c.error
        '''
        validation = fs.validate_on_edit(group_name, group_id)
        if not validation:
            errors = []            
            for field, err_list in fs.errors.items():
                errors.append("%s:%s" % (field.name, ";".join(err_list)))
            c.error = ', '.join(errors)
            c.form = self._render_edit_form(fs)
            raise ValidationException(c.error, fs)

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
            errors = []            
            for row, err in fs.errors.items():
                errors.append(err)
            c.error = ', '.join(errors)
            c.form = self._render_edit_form(fs)
            raise ValidationException(c.error, fs)
        try:
            fs.sync()
        except Exception, inst:
            model.Session.rollback()
            raise
        else:
            model.Session.commit()
