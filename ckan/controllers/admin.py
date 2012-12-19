from pylons import config

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.app_globals as app_globals
import ckan.lib.authztool
import ckan.model as model
import ckan.logic
import ckan.new_authz

from ckan.model.authz import Role
roles = Role.get_all()
role_tuples = [(x, x) for x in roles]


c = base.c
request = base.request
_ = base._

def get_sysadmins():
    q = model.Session.query(model.User).filter(model.User.sysadmin==True)
    return q.all()


class AdminController(base.BaseController):
    def __before__(self, action, **params):
        super(AdminController, self).__before__(action, **params)
        context = {'model': model,
                   'user': c.user}
        if not ckan.new_authz.is_authorized('sysadmin', context, {})['success']:
            base.abort(401, _('Need to be system administrator to administer'))
        c.revision_change_state_allowed = True

    def _get_config_form_items(self):
        # Styles for use in the form.select() macro.
        styles = [{'text': 'Default', 'value': '/base/css/main.css'},
                  {'text': 'Red', 'value': '/base/css/red.css'},
                  {'text': 'Green', 'value': '/base/css/green.css'},
                  {'text': 'Maroon', 'value': '/base/css/maroon.css'},
                  {'text': 'Fuchsia', 'value': '/base/css/fuchsia.css'}]
        items = [
            {'name': 'ckan.site_title', 'control': 'input', 'label': _('Site Title'), 'placeholder': _('')},
            {'name': 'ckan.main_css', 'control': 'select', 'options': styles, 'label': _('Style'), 'placeholder': _('')},
            {'name': 'ckan.site_description', 'control': 'input', 'label': _('Site Tag Line'), 'placeholder': _('')},
            {'name': 'ckan.site_logo', 'control': 'input', 'label': _('Site Tag Logo'), 'placeholder': _('')},
            {'name': 'ckan.site_about', 'control': 'markdown', 'label': _('About'), 'placeholder': _('About page text')},
            {'name': 'ckan.site_intro_text', 'control': 'markdown', 'label': _('Intro Text'), 'placeholder': _('Text on home page')},
            {'name': 'ckan.site_custom_css', 'control': 'textarea', 'label': _('Custom CSS'), 'placeholder': _('Customisable css inserted into the page header')},
        ]
        return items

    def reset_config(self):
        if 'cancel' in request.params:
            h.redirect_to(controller='admin', action='config')

        if request.method == 'POST':
            # remove sys info items
            for item in self._get_config_form_items():
                name = item['name']
                app_globals.delete_global(name)
            # reset to values in config
            app_globals.reset()
            h.redirect_to(controller='admin', action='config')

        return base.render('admin/confirm_reset.html')

    def config(self):

        items = self._get_config_form_items()
        data = request.POST
        if 'save' in data:
            # update config from form
            for item in items:
                name = item['name']
                if name in data:
                    app_globals.set_global(name, data[name])
            app_globals.reset()
            h.redirect_to(controller='admin', action='config')

        data = {}
        for item in items:
            name = item['name']
            data[name] = config.get(name)

        vars = {'data': data, 'errors': {}, 'form_items': items}
        return base.render('admin/config.html',
                           extra_vars = vars)

    def index(self):
        #now pass the list of sysadmins
        c.sysadmins = [a.name for a in get_sysadmins()]

        return base.render('admin/index.html')

    def authz(self):
        def action_save_form(users):
            # The permissions grid has been saved
            # which is a grid of checkboxes named user$role
            rpi = request.params.items()

            # The grid passes us a list of the users/roles that were displayed
            submitted = [a for (a, b) in rpi if (b == u'submitted')]
            # and also those which were checked
            checked = [a for (a, b) in rpi if (b == u'on')]

            # from which we can deduce true/false for each user/role
            # combination that was displayed in the form
            table_dict = {}
            for a in submitted:
                table_dict[a] = False
            for a in checked:
                table_dict[a] = True

            # now we'll split up the user$role strings to make a dictionary
            # from (user,role) to True/False, which tells us what we need to
            # do.
            new_user_role_dict = {}
            for (ur, val) in table_dict.items():
                u, r = ur.split('$')
                new_user_role_dict[(u, r)] = val

            # we get the current user/role assignments
            # and make a dictionary of them
            current_uors = model.Session.query(model.SystemRole).all()
            current_users_roles = [(uor.user.name, uor.role)
                                   for uor in current_uors
                                   if uor.user]

            current_user_role_dict = {}
            for (u, r) in current_users_roles:
                current_user_role_dict[(u, r)] = True

            # and now we can loop through our dictionary of desired states
            # checking whether a change needs to be made, and if so making it

            # WORRY: Here it seems that we have to check whether someone is
            # already assigned a role, in order to avoid assigning it twice,
            # or attempting to delete it when it doesn't exist. Otherwise
            # problems occur. However this doesn't affect the index page,
            # which would seem to be prone to suffer the same effect. Why
            # the difference?


            for ((u, r), val) in new_user_role_dict.items():
                if val:
                    if not ((u, r) in current_user_role_dict):
                        model.add_user_to_role(
                            model.User.by_name(u), r,
                            model.System())
                else:
                    if ((u, r) in current_user_role_dict):
                        model.remove_user_from_role(
                            model.User.by_name(u), r,
                            model.System())

            # finally commit the change to the database
            model.Session.commit()
            h.flash_success(_("Changes Saved"))

        if ('save' in request.POST):
            action_save_form('users')

        def action_add_form(users):
            # The user is attempting to set new roles for a named user
            new_user = request.params.get('new_user_name')
            # this is the list of roles whose boxes were ticked
            checked_roles = [a for (a, b) in request.params.items()
                             if (b == u'on')]
            # this is the list of all the roles that were in the submitted
            # form
            submitted_roles = [a for (a, b) in request.params.items()
                               if (b == u'submitted')]

            # from this we can make a dictionary of the desired states
            # i.e. true for the ticked boxes, false for the unticked
            desired_roles = {}
            for r in submitted_roles:
                desired_roles[r] = False
            for r in checked_roles:
                desired_roles[r] = True

            # again, in order to avoid either creating a role twice or
            # deleting one which is non-existent, we need to get the users'
            # current roles (if any)

            current_uors = model.Session.query(model.SystemRole).all()


            current_roles = [uor.role for uor in current_uors
                             if (uor.user and uor.user.name == new_user)]
            user_object = model.User.by_name(new_user)
            if user_object is None:
                # The submitted user does not exist. Bail with flash
                # message
                h.flash_error(_('unknown user:') + str(new_user))
            else:
                # Whenever our desired state is different from our
                # current state, change it.
                for (r, val) in desired_roles.items():
                    if val:
                        if (r not in current_roles):
                            model.add_user_to_role(user_object, r,
                                                   model.System())
                    else:
                        if (r in current_roles):
                            model.remove_user_from_role(user_object, r,
                                                        model.System())
                h.flash_success(_("User Added"))

            # and finally commit all these changes to the database
            model.Session.commit()

        if 'add' in request.POST:
            action_add_form('users')

        # =================
        # Display the page
        # Find out all the possible roles. For the system object that's just
        # all of them.
        possible_roles = Role.get_all()

        # get the list of users who have roles on the System, with their roles
        uors = model.Session.query(model.SystemRole).all()
        # uniquify and sort
        users = sorted(list(set([uor.user.name for uor in uors if uor.user])))

        users_roles = [(uor.user.name, uor.role) for uor in uors if uor.user]
        user_role_dict = {}
        for u in users:
            for r in possible_roles:
                if (u, r) in users_roles:
                    user_role_dict[(u, r)] = True
                else:
                    user_role_dict[(u, r)] = False


        # pass these variables to the template for rendering
        c.roles = possible_roles
        c.users = users
        c.user_role_dict = user_role_dict

        return base.render('admin/authz.html')

    def trash(self):
        c.deleted_revisions = model.Session.query(
            model.Revision).filter_by(state=model.State.DELETED)
        c.deleted_packages = model.Session.query(
            model.Package).filter_by(state=model.State.DELETED)
        if not request.params or (len(request.params) == 1 and '__no_cache__'
                                  in request.params):
            return base.render('admin/trash.html')
        else:
            # NB: we repeat retrieval of of revisions
            # this is obviously inefficient (but probably not *that* bad)
            # but has to be done to avoid (odd) sqlalchemy errors (when doing
            # purge packages) of form: "this object already exists in the
            # session"
            msgs = []
            if ('purge-packages' in request.params) or ('purge-revisions' in
                                                        request.params):
                if 'purge-packages' in request.params:
                    revs_to_purge = []
                    for pkg in c.deleted_packages:
                        revisions = [x[0] for x in pkg.all_related_revisions]
                        # ensure no accidental purging of other(non-deleted)
                        # packages initially just avoided purging revisions
                        # where non-deleted packages were affected
                        # however this lead to confusing outcomes e.g.
                        # we succesfully deleted revision in which package
                        # was deleted (so package now active again) but no
                        # other revisions
                        problem = False
                        for r in revisions:
                            affected_pkgs = set(r.packages).\
                                difference(set(c.deleted_packages))
                            if affected_pkgs:
                                msg = _('Cannot purge package %s as '
                                        'associated revision %s includes '
                                        'non-deleted packages %s')
                                msg = msg % (pkg.id, r.id, [pkg.id for r
                                                            in affected_pkgs])
                                msgs.append(msg)
                                problem = True
                                break
                        if not problem:
                            revs_to_purge += [r.id for r in revisions]
                    model.Session.remove()
                else:
                    revs_to_purge = [rev.id for rev in c.deleted_revisions]
                revs_to_purge = list(set(revs_to_purge))
                for id in revs_to_purge:
                    revision = model.Session.query(model.Revision).get(id)
                    try:
                        # TODO deleting the head revision corrupts the edit
                        # page Ensure that whatever 'head' pointer is used
                        # gets moved down to the next revision
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
