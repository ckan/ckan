import genshi

from sqlalchemy.orm import eagerload_all
from ckan.lib.base import BaseController, c, model, request, render, h
from ckan.lib.base import ValidationException, abort
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

    def __init__(self):
        BaseController.__init__(self)
        self.extensions = PluginImplementations(IGroupController)
    
    def index(self):
        
        if not self.authorizer.am_authorized(c, model.Action.SITE_READ, model.System):
            abort(401, _('Not authorized to see this page'))
        
        query = authz.Authorizer().authorized_query(c.user, model.Group)
        query = query.order_by(model.Group.name.asc())
        query = query.order_by(model.Group.title.asc())
        query = query.options(eagerload_all('packages'))
        c.page = Page(
            collection=query,
            page=request.params.get('page', 1),
            items_per_page=20
        )
        return render('group/index.html')


    def read(self, id):
        c.group = model.Group.get(id)
        if c.group is None:
            abort(404)
        auth_for_read = self.authorizer.am_authorized(c, model.Action.READ, c.group)
        if not auth_for_read:
            abort(401, _('Not authorized to read %s') % id.encode('utf8'))
        
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
        for extension in self.extensions:
            extension.read(c.group)
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
                   'id': id}

        if context['save'] and not data:
            return self._save_edit(id, context)

        try:
            old_data = get.group_show(context)
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
            group = create.group_create(data_dict, context)
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
            group = update.group_update(data_dict, context)
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
        c.group = model.Group.get(id)
        if c.group is None:
            abort(404, _('Group not found'))
        
        c.groupname = c.group.name
        c.grouptitle = c.group.display_name

        c.authz_editable = self.authorizer.am_authorized(c, model.Action.EDIT_PERMISSIONS, c.group)
        if not c.authz_editable:
            abort(401, _('Not authorized to edit authorization for group'))

        if 'save' in request.params: # form posted
            # needed because request is nested
            # multidict which is read only
            params = dict(request.params)
            c.fs = ckan.forms.get_authz_fieldset('group_authz_fs').bind(c.group.roles, data=params or None)
            try:
                self._update_authz(c.fs)
            except ValidationException, error:
                # TODO: sort this out 
                # fs = error.args[0]
                # return render('group/authz.html')
                raise
            # now do new roles
            newrole_user_id = request.params.get('GroupRole--user_id')
            newrole_authzgroup_id = request.params.get('GroupRole--authorized_group_id')
            if newrole_user_id != '__null_value__' and newrole_authzgroup_id != '__null_value__':
                c.message = _(u'Please select either a user or an authorization group, not both.')
            elif newrole_user_id != '__null_value__':
                user = model.Session.query(model.User).get(newrole_user_id)
                # TODO: chech user is not None (should go in validation ...)
                role = request.params.get('GroupRole--role')
                newgrouprole = model.GroupRole(user=user, group=c.group,
                        role=role)
                # With FA no way to get new GroupRole back to set group attribute
                # new_roles = ckan.forms.new_roles_fs.bind(model.GroupRole, data=params or None)
                # new_roles.sync()
                for extension in self.extensions:
                    extension.authz_add_role(newgrouprole)
                model.Session.commit()
                model.Session.remove()
                c.message = _(u'Added role \'%s\' for user \'%s\'') % (
                    newgrouprole.role,
                    newgrouprole.user.display_name)
            elif newrole_authzgroup_id != '__null_value__':
                authzgroup = model.Session.query(model.AuthorizationGroup).get(newrole_authzgroup_id)
                # TODO: chech user is not None (should go in validation ...)
                role = request.params.get('GroupRole--role')
                newgrouprole = model.GroupRole(authorized_group=authzgroup, 
                        group=c.group, role=role)
                # With FA no way to get new GroupRole back to set group attribute
                # new_roles = ckan.forms.new_roles_fs.bind(model.GroupRole, data=params or None)
                # new_roles.sync()
                for extension in self.extensions:
                    extension.authz_add_role(newgrouprole)
                model.Session.commit()
                model.Session.remove()
                c.message = _(u'Added role \'%s\' for authorization group \'%s\'') % (
                    newgrouprole.role,
                    newgrouprole.authorized_group.name)
        elif 'role_to_delete' in request.params:
            grouprole_id = request.params['role_to_delete']
            grouprole = model.Session.query(model.GroupRole).get(grouprole_id)
            if grouprole is None:
                c.error = _(u'Error: No role found with that id')
            else:
                for extension in self.extensions:
                    extension.authz_remove_role(grouprole)
                grouprole.purge()
                if grouprole.user:
                    c.message = _(u'Deleted role \'%s\' for user \'%s\'') % \
                                (grouprole.role, grouprole.user.display_name)
                elif grouprole.authorized_group:
                    c.message = _(u'Deleted role \'%s\' for authorization group \'%s\'') % \
                                (grouprole.role, grouprole.authorized_group.name)
                model.Session.commit()

        # retrieve group again ...
        c.group = model.Group.get(id)
        fs = ckan.forms.get_authz_fieldset('group_authz_fs').bind(c.group.roles)
        c.form = fs.render()
        c.new_roles_form = \
            ckan.forms.get_authz_fieldset('new_group_roles_fs').render()
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

        c.group = model.Group.get(id)
        if not c.group:
            abort(404, _('Group not found'))
        if not self.authorizer.am_authorized(c, model.Action.READ, c.group):
            abort(401, _('User %r not authorized to edit %r') % (c.user, id))

        format = request.params.get('format', '')
        if format == 'atom':
            # Generate and return Atom 1.0 document.
            from webhelpers.feedgenerator import Atom1Feed
            feed = Atom1Feed(
                title=_(u'CKAN Group Revision History'),
                link=h.url_for(controller='group', action='read', id=c.group.name),
                description=_(u'Recent changes to CKAN Group: ') +
                    c.group.display_name,
                language=unicode(get_lang()),
            )
            for revision, obj_rev in c.group.all_related_revisions:
                try:
                    dayHorizon = int(request.params.get('days'))
                except:
                    dayHorizon = 30
                try:
                    dayAge = (datetime.now() - revision.timestamp).days
                except:
                    dayAge = 0
                if dayAge >= dayHorizon:
                    break
                if revision.message:
                    item_title = u'%s' % revision.message.split('\n')[0]
                else:
                    item_title = u'%s' % revision.id
                item_link = h.url_for(controller='revision', action='read', id=revision.id)
                item_description = _('Log message: ')
                item_description += '%s' % (revision.message or '')
                item_author_name = revision.author
                item_pubdate = revision.timestamp
                feed.add_item(
                    title=item_title,
                    link=item_link,
                    description=item_description,
                    author_name=item_author_name,
                    pubdate=item_pubdate,
                )
            feed.content_type = 'application/atom+xml'
            return feed.writeString('utf-8')
        c.group_revisions = c.group.all_related_revisions
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
