import genshi

from sqlalchemy.orm import eagerload_all
from ckan.lib.base import *
from pylons.i18n import get_lang, _
import ckan.authz as authz
import ckan.forms
from ckan.lib.helpers import Page
from ckan.logic import NotAuthorized, check_access

class AuthorizationGroupController(BaseController):
    
    def __init__(self):
        BaseController.__init__(self)
    
    def index(self):
        from ckan.lib.helpers import Page
        try:
            context = {'model':model,'user': c.user or c.author}
            check_access('site_read',context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        query = ckan.authz.Authorizer().authorized_query(c.user, model.AuthorizationGroup)
        query = query.options(eagerload_all('users'))
        c.page = Page(
            collection=query,
            page=request.params.get('page', 1),
            items_per_page=20
        )
        return render('authorization_group/index.html')

    def _get_authgroup_by_name_or_id(self, id):
        return model.AuthorizationGroup.by_name(id) or\
               model.Session.query(model.AuthorizationGroup).get(id)

    def read(self, id):
        c.authorization_group = self._get_authgroup_by_name_or_id(id)
        if c.authorization_group is None:
            abort(404)
        auth_for_read = self.authorizer.am_authorized(c, model.Action.READ, 
                                                      c.authorization_group)
        if not auth_for_read:
            abort(401, _('Not authorized to read %s') % id.encode('utf8'))
        
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
            abort(401, _('Unauthorized to create a group'))
        
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
            authorization_group.users = list(set(users))
            usernames = request.params.getall('AuthorizationGroupUser--user_name')
            for username in usernames:
                if username:
                    usr = model.User.by_name(username)
                    if usr and usr not in authorization_group.users:
                        model.add_user_to_authorization_group(usr, authorization_group, model.Role.READER)
            model.repo.commit_and_remove()
            h.redirect_to(controller='authorization_group', action='read', id=c.authzgroupname)

        c.form = self._render_edit_form(fs)
        return render('authorization_group/new.html')

    def edit(self, id=None): # allow id=None to allow posting
        c.error = ''
        authorization_group = self._get_authgroup_by_name_or_id(id)
        if authorization_group is None:
            abort(404, '404 Not Found')
        am_authz = self.authorizer.am_authorized(c, model.Action.EDIT, authorization_group)
        if not am_authz:
            abort(401, _('User %r not authorized to edit %r') % (c.user, id))
            
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
            authorization_group.users = list(set(users))
            usernames = request.params.getall('AuthorizationGroupUser--user_name')
            for username in usernames:
                if username:
                    usr = model.User.by_name(username)
                    if usr and usr not in authorization_group.users:
                        model.add_user_to_authorization_group(usr, authorization_group, model.Role.READER)
            model.repo.commit_and_remove()
            h.redirect_to(controller='authorization_group', action='read', id=c.authorization_group_name)

    def authz(self, id):
        authorization_group = self._get_authgroup_by_name_or_id(id)
        if authorization_group is None:
            abort(404, _('Group not found'))

        c.authorization_group_name = authorization_group.name

        c.authz_editable = self.authorizer.am_authorized(c, model.Action.EDIT_PERMISSIONS, 
                                                         authorization_group)
        if not c.authz_editable:
            abort(401, gettext('User %r not authorized to edit %s authorizations') % (c.user, id))

        roles = self._handle_update_of_authz(authorization_group)
        self._prepare_authz_info_for_render(roles)
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
