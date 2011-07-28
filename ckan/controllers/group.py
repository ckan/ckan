import genshi
import datetime

from sqlalchemy.orm import eagerload_all
from ckan.lib.base import BaseController, c, model, request, render, h
from ckan.lib.base import ValidationException, abort, gettext
from pylons.i18n import get_lang, _
import ckan.authz as authz
from ckan.authz import Authorizer
from ckan.lib.helpers import Page
from ckan.plugins import PluginImplementations, IGroupController
import ckan.logic.action.create as create
import ckan.logic.action.update as update
import ckan.logic.action.get as get
from ckan.lib.navl.dictization_functions import DataError, unflatten, validate
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic.schema import group_form_schema
from ckan.logic import tuplize_dict, clean_dict, parse_params
import ckan.forms

class GroupController(BaseController):

    ## hooks for subclasses 
    group_form = 'group/new_group_form.html'

    def _form_to_db_schema(self):
        return group_form_schema()

    def _db_to_form_schema(self):
        '''This is an interface to manipulate data from the database
        into a format suitable for the form (optional)'''

    def _setup_template_variables(self, context):
        c.is_sysadmin = Authorizer().is_sysadmin(c.user)

        ## This is messy as auths take domain object not data_dict
        group = context.get('group') or c.pkg
        if group:
            c.auth_for_change_state = Authorizer().am_authorized(
                c, model.Action.CHANGE_STATE, group)

    ## end hooks
    
    def index(self):

        if not self.authorizer.am_authorized(c, model.Action.SITE_READ, model.System):
            abort(401, _('Not authorized to see this page'))

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}

        data_dict = {'all_fields': True}
               
        results = get.group_list(context,data_dict)

        c.page = Page(
            collection=results,
            page=request.params.get('page', 1),
            items_per_page=20
        )
        return render('group/index.html')


    def read(self, id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self._form_to_db_schema()}
        data_dict = {'id': id}
        try:
            c.group_dict = get.group_show(context, data_dict)
            c.group = context['group']
        except NotFound:
            abort(404, _('Group not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % id)
        
        try:
 
            desc_formatted = ckan.misc.MarkdownFormat().to_html(c.group.description)
            desc_formatted = genshi.HTML(desc_formatted)
        except genshi.ParseError, e:
            log.error('Could not print group description: %r Error: %r', c.group.description, e)
            desc_formatted = 'Error: Could not parse group description'
        c.group_description_formatted = desc_formatted
        c.group_admins = self.authorizer.get_admins(c.group)

        c.page = Page(
            collection=c.group.active_packages(),
            page=request.params.get('page', 1),
            items_per_page=50
        )

        return render('group/read.html')

    def new(self, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'schema': self._form_to_db_schema(),
                   'save': 'save' in request.params}

        auth_for_create = Authorizer().am_authorized(c, model.Action.GROUP_CREATE, model.System())
        if not auth_for_create:
            abort(401, _('Unauthorized to create a group'))

        if context['save'] and not data:
            return self._save_new(context)
        
        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}

        self._setup_template_variables(context)
        c.form = render(self.group_form, extra_vars=vars)
        return render('group/new.html')

    def edit(self, id, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'save': 'save' in request.params,
                   'schema': self._form_to_db_schema(),
                   }
        data_dict = {'id': id}

        if context['save'] and not data:
            return self._save_edit(id, context)

        try:
            old_data = get.group_show(context, data_dict)
            c.grouptitle = old_data.get('title')
            c.groupname = old_data.get('name')
            schema = self._db_to_form_schema()
            if schema:
                old_data, errors = validate(old_data, schema)

            data = data or old_data

        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % '')

        group = context.get("group")

        am_authz = self.authorizer.am_authorized(c, model.Action.EDIT, group)
        if not am_authz:
            abort(401, _('User %r not authorized to edit %s') % (c.user, id))

        errors = errors or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}

        self._setup_template_variables(context)
        c.form = render(self.group_form, extra_vars=vars)
        return render('group/edit.html')

    def _save_new(self, context):
        try:
            data_dict = clean_dict(unflatten(
                tuplize_dict(parse_params(request.params))))
            context['message'] = data_dict.get('log_message', '')
            group = create.group_create(context, data_dict)
            h.redirect_to(controller='group', action='read', id=group['name'])
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % '')
        except NotFound, e:
            abort(404, _('Package not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.new(data_dict, errors, error_summary)

    def _save_edit(self, id, context):
        try:
            data_dict = clean_dict(unflatten(
                tuplize_dict(parse_params(request.params))))
            context['message'] = data_dict.get('log_message', '')
            data_dict['id'] = id
            group = update.group_update(context, data_dict)
            h.redirect_to(controller='group', action='read', id=group['name'])
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % id)
        except NotFound, e:
            abort(404, _('Package not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.edit(id, data_dict, errors, error_summary)

    def authz(self, id):
        group = model.Group.get(id)
        if group is None:
            abort(404, _('Group not found'))
        c.groupname = group.name
        c.grouptitle = group.display_name

        c.authz_editable = self.authorizer.am_authorized(c, model.Action.EDIT_PERMISSIONS, group)
        if not c.authz_editable:
            abort(401, gettext('User %r not authorized to edit %s authorizations') % (c.user, id))
 

        #see package.py for comments
        def get_userobjectroles():
            group = model.Group.get(id)
            uors = model.Session.query(model.GroupRole).join('group').filter_by(name=group.name).all()
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
                            model.add_user_to_role(model.User.by_name(u),r,group)
                    else:
                        if ((u,r) in current_user_role_dict):
                            model.remove_user_from_role(model.User.by_name(u),r,group)
            elif users_or_authz_groups=='authz_groups':
                for ((u,r), val) in new_user_role_dict.items():
                    if val:
                        if not ((u,r) in current_user_role_dict):
                            model.add_authorization_group_to_role(model.AuthorizationGroup.by_name(u),r,group)
                    else:
                        if ((u,r) in current_user_role_dict):
                            model.remove_authorization_group_from_role(model.AuthorizationGroup.by_name(u),r,group)
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
                                model.add_user_to_role(user_object, r, group)
                        else:
                            if (r in current_roles):
                                model.remove_user_from_role(user_object, r, group)
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
                                model.add_authorization_group_to_role(user_object, r, group)
                        else:
                            if (r in current_roles):
                                model.remove_authorization_group_from_role(user_object, r, group)
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

        return render('group/authz.html')
       
    def history(self, id):
        if 'diff' in request.params or 'selected1' in request.params:
            try:
                params = {'id':request.params.getone('group_name'),
                          'diff':request.params.getone('selected1'),
                          'oldid':request.params.getone('selected2'),
                          }
            except KeyError, e:
                if dict(request.params).has_key('group_name'):
                    id = request.params.getone('group_name')
                c.error = _('Select two revisions before doing the comparison.')
            else:
                params['diff_entity'] = 'group'
                h.redirect_to(controller='revision', action='diff', **params)

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self._form_to_db_schema()}
        data_dict = {'id': id}
        try:
            c.group_dict = get.group_show(context, data_dict)
            c.group_revisions = get.group_revision_list(context, data_dict)
            #TODO: remove
            # Still necessary for the authz check in group/layout.html
            c.group = context['group']
        except NotFound:
            abort(404, _('Group not found'))
        except NotAuthorized:
            abort(401, _('User %r not authorized to edit %r') % (c.user, id))

        format = request.params.get('format', '')
        if format == 'atom':
            # Generate and return Atom 1.0 document.
            from webhelpers.feedgenerator import Atom1Feed
            feed = Atom1Feed(
                title=_(u'CKAN Group Revision History'),
                link=h.url_for(controller='group', action='read', id=c.group_dict['name']),
                description=_(u'Recent changes to CKAN Group: ') +
                    c.group_dict['display_name'],
                language=unicode(get_lang()),
            )
            for revision_dict in c.group_revisions:
                revision_date = h.date_str_to_datetime(revision_dict['timestamp'])
                try:
                    dayHorizon = int(request.params.get('days'))
                except:
                    dayHorizon = 30
                dayAge = (datetime.datetime.now() - revision_date).days
                if dayAge >= dayHorizon:
                    break
                if revision_dict['message']:
                    item_title = u'%s' % revision_dict['message'].split('\n')[0]
                else:
                    item_title = u'%s' % revision_dict['id']
                item_link = h.url_for(controller='revision', action='read', id=revision_dict['id'])
                item_description = _('Log message: ')
                item_description += '%s' % (revision_dict['message'] or '')
                item_author_name = revision_dict['author']
                item_pubdate = revision_date
                feed.add_item(
                    title=item_title,
                    link=item_link,
                    description=item_description,
                    author_name=item_author_name,
                    pubdate=item_pubdate,
                )
            feed.content_type = 'application/atom+xml'
            return feed.writeString('utf-8')
        return render('group/history.html')

    def _render_edit_form(self, fs):
        # errors arrive in c.error and fs.errors
        c.fieldset = fs
        c.fieldset2 = ckan.forms.get_package_group_fieldset()
        return render('group/edit_form.html')

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
