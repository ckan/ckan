from ckan.lib.base import *
import ckan.authz
import ckan.lib.authztool
import ckan.model as model

from ckan.model.authz import Role
roles = Role.get_all()
role_tuples = [(x,x) for x in roles]

def get_sysadmins():
    q = model.Session.query(model.SystemRole).filter_by(role=model.Role.ADMIN)
    return [uor.user for uor in q.all() if uor.user]


class AdminController(BaseController):
    def __before__(self, action, **params):
        super(AdminController, self).__before__(action, **params)
        if not ckan.authz.Authorizer().is_sysadmin(unicode(c.user)):
            abort(401, _('Need to be system administrator to administer'))        
        c.revision_change_state_allowed = (
            c.user and
            self.authorizer.is_authorized(c.user, model.Action.CHANGE_STATE,
                model.Revision)
            )

    def index(self):
        #now pass the list of sysadmins 
        c.sysadmins = [a.name for a in get_sysadmins()]
   
        return render('admin/index.html')


    def authz(self):
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
            current_uors = model.Session.query(model.SystemRole).all()

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

            # WORRY: Here it seems that we have to check whether someone is already assigned
            # a role, in order to avoid assigning it twice, or attempting to delete it when
            # it doesn't exist. Otherwise problems occur. However this doesn't affect the 
            # index page, which would seem to be prone to suffer the same effect. 
            # Why the difference?

            if users_or_authz_groups=='users':
                for ((u,r), val) in new_user_role_dict.items():
                    if val:
                        if not ((u,r) in current_user_role_dict):
                            model.add_user_to_role(model.User.by_name(u),r,model.System())
                    else:
                        if ((u,r) in current_user_role_dict):
                            model.remove_user_from_role(model.User.by_name(u),r,model.System())
            elif users_or_authz_groups=='authz_groups':
                for ((u,r), val) in new_user_role_dict.items():
                    if val:
                        if not ((u,r) in current_user_role_dict):
                            model.add_authorization_group_to_role(model.AuthorizationGroup.by_name(u),r,model.System())
                    else:
                        if ((u,r) in current_user_role_dict):
                            model.remove_authorization_group_from_role(model.AuthorizationGroup.by_name(u),r,model.System())
            else:
                assert False, "shouldn't be here"


            # finally commit the change to the database
            model.Session.commit()
            h.flash_success(_("Changes Saved"))

        if ('save' in request.POST):
            action_save_form('users')

        if ('authz_save' in request.POST):
            action_save_form('authz_groups')




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
            
            current_uors = model.Session.query(model.SystemRole).all()

            if users_or_authz_groups=='users':
                current_roles = [uor.role for uor in current_uors if ( uor.user and uor.user.name == new_user )]
                user_object = model.User.by_name(new_user)
                if user_object==None:
                    # The submitted user does not exist. Bail with flash message
                    h.flash_error(_('unknown user:') + str (new_user))
                else:
                    # Whenever our desired state is different from our current state, change it.
                    for (r,val) in desired_roles.items():
                        if val:
                            if (r not in current_roles):
                                model.add_user_to_role(user_object, r, model.System())
                        else:
                            if (r in current_roles):
                                model.remove_user_from_role(user_object, r, model.System())
                    h.flash_success(_("User Added"))

            elif users_or_authz_groups=='authz_groups':
                current_roles = [uor.role for uor in current_uors if ( uor.authorized_group and uor.authorized_group.name == new_user )]
                user_object = model.AuthorizationGroup.by_name(new_user)
                if user_object==None:
                    # The submitted user does not exist. Bail with flash message
                    h.flash_error(_('unknown authorization group:') + str (new_user))
                else:
                    # Whenever our desired state is different from our current state, change it.
                    for (r,val) in desired_roles.items():
                        if val:
                            if (r not in current_roles):
                                model.add_authorization_group_to_role(user_object, r, model.System())
                        else:
                            if (r in current_roles):
                                model.remove_authorization_group_from_role(user_object, r, model.System())
                    h.flash_success(_("Authorization Group Added"))


            else:
                assert False, "shouldn't be here"










            # and finally commit all these changes to the database
            model.Session.commit()

        if 'add' in request.POST:
            action_add_form('users')
        if 'authz_add' in request.POST:
            action_add_form('authz_groups')


        # =================
        # Display the page

        # Find out all the possible roles. For the system object that's just all of them.
        possible_roles = Role.get_all()

        # get the list of users who have roles on the System, with their roles
        uors = model.Session.query(model.SystemRole).all()
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
    
        return render('admin/authz.html')

    def trash(self):
        c.deleted_revisions = model.Session.query(
                model.Revision).filter_by(state=model.State.DELETED)
        c.deleted_packages = model.Session.query(
                model.Package).filter_by(state=model.State.DELETED)
        if not request.params:
            return render('admin/trash.html')
        else:
            # NB: we repeat retrieval of of revisions
            # this is obviously inefficient (but probably not *that* bad)
            # but has to be done to avoid (odd) sqlalchemy errors (when doing
            # purge packages) of form: "this object already exists in the
            # session"
            msgs = []
            if ('purge-packages' in request.params) or ('purge-revisions' in request.params):
                if 'purge-packages' in request.params:
                    revs_to_purge = []
                    for pkg in c.deleted_packages:
                        revisions = [ x[0] for x in pkg.all_related_revisions ]
                        # ensure no accidental purging of other(non-deleted) packages
                        # initially just avoided purging revisions where
                        # non-deleted packages were affected
                        # however this lead to confusing outcomes e.g.
                        # we succesfully deleted revision in which package was deleted (so package
                        # now active again) but no other revisions
                        problem = False
                        for r in revisions:
                            affected_pkgs = set(r.packages).difference(set(c.deleted_packages))
                            if affected_pkgs:
                                msg = _('Cannot purge package %s as '
                                    'associated revision %s includes non-deleted packages %s')
                                msg = msg % (pkg.id, r.id, [pkg.id for r in affected_pkgs])
                                msgs.append(msg)
                                problem = True
                                break
                        if not problem:
                            revs_to_purge += [ r.id for r in revisions ]
                    model.Session.remove()
                else:
                    revs_to_purge = [ rev.id for rev in c.deleted_revisions ]
                revs_to_purge = list(set(revs_to_purge))
                for id in revs_to_purge:
                    revision = model.Session.query(model.Revision).get(id)
                    try:
                        # TODO deleting the head revision corrupts the edit page
                        # Ensure that whatever 'head' pointer is used gets moved down to the next revision
                        model.repo.purge_revision(revision, leave_record=False)
                    except Exception, inst:
                        msg = _('Problem purging revision %s: %s') % (id, inst)
                        msgs.append(msg)
                h.flash_success(_('Purge complete'))
            else:
                msgs.append(_('Action not implemented.'))

            for msg in msgs:
                h.flash_error(msg)
            h.redirect_to(h.url_for('ckanadmin', action='trash'))

