import genshi

from sqlalchemy.orm import eagerload_all
from ckan.lib.base import *
from pylons.i18n import get_lang, _
import ckan.authz as authz
import ckan.forms
from ckan.lib.helpers import Page

class AuthorizationGroupController(BaseController):
    
    def __init__(self):
        BaseController.__init__(self)
    
    def index(self):
        from ckan.lib.helpers import Page

        if not self.authorizer.am_authorized(c, model.Action.SITE_READ, model.System):
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
            h.redirect_to(action='read', id=c.authzgroupname)

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
            h.redirect_to(action='read', id=c.authorization_group_name)

    def authz(self, id):
        authorization_group = self._get_authgroup_by_name_or_id(id)
        if authorization_group is None:
            abort(404, _('Group not found'))

        c.authorization_group_name = authorization_group.name

        c.authz_editable = self.authorizer.am_authorized(c, model.Action.EDIT_PERMISSIONS, 
                                                         authorization_group)

        if not c.authz_editable:
            abort(401, gettext('User %r not authorized to edit %s authorizations') % (c.user, id))

        #see package.py for comments
        def get_userobjectroles():
            authorization_group = self._get_authgroup_by_name_or_id(id)
            uors = model.Session.query(model.AuthorizationGroupRole).join('authorization_group').filter_by(name=authorization_group.name).all()
            return uors

        def action_save_form(users_or_authz_groups):
            # The permissions grid has been saved
            # which is a grid of checkboxes named user$role
            rpi = request.params.items()

            # The grid passes us a list of the users/roles that were displayed
            submitted = [ a for (a,b) in rpi if (b == u'submitted')]
            # and also those which were checked
            checked = [ a for (a,b) in rpi if (b == u'on')]

            # from which we can deduce true/false for each user/role combination
            # that was displayed in the form
            table_dict={}
            for a in submitted:
                table_dict[a]=False
            for a in checked:
                table_dict[a]=True

            # now we'll split up the user$role strings to make a dictionary from 
            # (user,role) to True/False, which tells us what we need to do.
            new_user_role_dict={}
            for (ur,val) in table_dict.items():
                u,r = ur.split('$')
                new_user_role_dict[(u,r)] = val
               
            # we get the current user/role assignments 
            # and make a dictionary of them
            current_uors = get_userobjectroles()

            if users_or_authz_groups=='users':
                current_users_roles = [( uor.user.name, uor.role) for uor in current_uors if uor.user]
            elif users_or_authz_groups=='authz_groups':
                current_users_roles = [( uor.authorized_group.name, uor.role) for uor in current_uors if uor.authorized_group]        
            else:
                assert False, "shouldn't be here"

            current_user_role_dict={}
            for (u,r) in current_users_roles:
                current_user_role_dict[(u,r)]=True

            # and now we can loop through our dictionary of desired states
            # checking whether a change needs to be made, and if so making it

            # Here we check whether someone is already assigned a role, in order
            # to avoid assigning it twice, or attempting to delete it when it
            # doesn't exist. Otherwise problems can occur.
            if users_or_authz_groups=='users':
                for ((u,r), val) in new_user_role_dict.items():
                    if val:
                        if not ((u,r) in current_user_role_dict):
                            model.add_user_to_role(model.User.by_name(u),r,authorization_group)
                    else:
                        if ((u,r) in current_user_role_dict):
                            model.remove_user_from_role(model.User.by_name(u),r,authorization_group)
            elif users_or_authz_groups=='authz_groups':
                for ((u,r), val) in new_user_role_dict.items():
                    if val:
                        if not ((u,r) in current_user_role_dict):
                            model.add_authorization_group_to_role(model.AuthorizationGroup.by_name(u),r,authorization_group)
                    else:
                        if ((u,r) in current_user_role_dict):
                            model.remove_authorization_group_from_role(model.AuthorizationGroup.by_name(u),r,authorization_group)
            else:
                assert False, "shouldn't be here"

            # finally commit the change to the database
            model.repo.commit_and_remove()
            h.flash_success("Changes Saved")



        def action_add_form(users_or_authz_groups):
            # The user is attempting to set new roles for a named user
            new_user = request.params.get('new_user_name')
            # this is the list of roles whose boxes were ticked
            checked_roles = [ a for (a,b) in request.params.items() if (b == u'on')]
            # this is the list of all the roles that were in the submitted form
            submitted_roles = [ a for (a,b) in request.params.items() if (b == u'submitted')]

            # from this we can make a dictionary of the desired states
            # i.e. true for the ticked boxes, false for the unticked
            desired_roles = {}
            for r in submitted_roles:
                desired_roles[r]=False
            for r in checked_roles:
                desired_roles[r]=True

            # again, in order to avoid either creating a role twice or deleting one which is
            # non-existent, we need to get the users' current roles (if any)
  
            current_uors = get_userobjectroles()

            if users_or_authz_groups=='users':
                current_roles = [uor.role for uor in current_uors if ( uor.user and uor.user.name == new_user )]
                user_object = model.User.by_name(new_user)
                if user_object==None:
                    # The submitted user does not exist. Bail with flash message
                    h.flash_error('unknown user:' + str (new_user))
                else:
                    # Whenever our desired state is different from our current state, change it.
                    for (r,val) in desired_roles.items():
                        if val:
                            if (r not in current_roles):
                                model.add_user_to_role(user_object, r, authorization_group)
                        else:
                            if (r in current_roles):
                                model.remove_user_from_role(user_object, r, authorization_group)
                    h.flash_success("User Added")

            elif users_or_authz_groups=='authz_groups':
                current_roles = [uor.role for uor in current_uors if ( uor.authorized_group and uor.authorized_group.name == new_user )]
                user_object = model.AuthorizationGroup.by_name(new_user)
                if user_object==None:
                    # The submitted user does not exist. Bail with flash message
                    h.flash_error('unknown authorization group:' + str (new_user))
                else:
                    # Whenever our desired state is different from our current state, change it.
                    for (r,val) in desired_roles.items():
                        if val:
                            if (r not in current_roles):
                                model.add_authorization_group_to_role(user_object, r, authorization_group)
                        else:
                            if (r in current_roles):
                                model.remove_authorization_group_from_role(user_object, r, authorization_group)
                    h.flash_success("Authorization Group Added")

            else:
                assert False, "shouldn't be here"

            # and finally commit all these changes to the database
            model.repo.commit_and_remove()


        # In the event of a post request, work out which of the four possible actions
        # is to be done, and do it before displaying the page
        if 'add' in request.POST:
            action_add_form('users')

        if 'authz_add' in request.POST:
            action_add_form('authz_groups')

        if 'save' in request.POST:
            action_save_form('users')

        if 'authz_save' in request.POST:
            action_save_form('authz_groups')

        # =================
        # Display the page

        # Find out all the possible roles. At the moment, any role can be
        # associated with any object, so that's easy:
        possible_roles = model.Role.get_all()

        # get the list of users who have roles on this object, with their roles
        uors = get_userobjectroles()

        # uniquify and sort
        users = sorted(list(set([uor.user.name for uor in uors if uor.user])))
        authz_groups = sorted(list(set([uor.authorized_group.name for uor in uors if uor.authorized_group])))

        # make a dictionary from (user, role) to True, False
        users_roles = [( uor.user.name, uor.role) for uor in uors if uor.user]
        user_role_dict={}
        for u in users:
            for r in possible_roles:
                if (u,r) in users_roles:
                    user_role_dict[(u,r)]=True
                else:
                    user_role_dict[(u,r)]=False

        # and similarly make a dictionary from (authz_group, role) to True, False
        authz_groups_roles = [( uor.authorized_group.name, uor.role) for uor in uors if uor.authorized_group]
        authz_groups_role_dict={}
        for u in authz_groups:
            for r in possible_roles:
                if (u,r) in authz_groups_roles:
                    authz_groups_role_dict[(u,r)]=True
                else:
                    authz_groups_role_dict[(u,r)]=False

        # pass these variables to the template for rendering
        c.roles = possible_roles

        c.users = users
        c.user_role_dict = user_role_dict

        c.authz_groups = authz_groups
        c.authz_groups_role_dict = authz_groups_role_dict

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
