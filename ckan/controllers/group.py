import re
import os
import logging
import genshi
import cgi
import datetime
from urllib import urlencode

from pylons.i18n import get_lang

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.maintain as maintain
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.lib.search as search
import ckan.model as model
import ckan.new_authz as new_authz
import ckan.lib.plugins
import ckan.plugins as plugins
from ckan.common import OrderedDict, c, g, request, _

log = logging.getLogger(__name__)

render = base.render
abort = base.abort

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params

lookup_group_plugin = ckan.lib.plugins.lookup_group_plugin


class GroupController(base.BaseController):

    group_type = 'group'

    ## hooks for subclasses

    def _group_form(self, group_type=None):
        return lookup_group_plugin(group_type).group_form()

    def _form_to_db_schema(self, group_type=None):
        return lookup_group_plugin(group_type).form_to_db_schema()

    def _db_to_form_schema(self, group_type=None):
        '''This is an interface to manipulate data from the database
        into a format suitable for the form (optional)'''
        return lookup_group_plugin(group_type).db_to_form_schema()

    def _setup_template_variables(self, context, data_dict, group_type=None):
        return lookup_group_plugin(group_type).\
            setup_template_variables(context, data_dict)

    def _new_template(self, group_type):
        return lookup_group_plugin(group_type).new_template()

    def _index_template(self, group_type):
        return lookup_group_plugin(group_type).index_template()

    def _about_template(self, group_type):
        return lookup_group_plugin(group_type).about_template()

    def _read_template(self, group_type):
        return lookup_group_plugin(group_type).read_template()

    def _history_template(self, group_type):
        return lookup_group_plugin(group_type).history_template()

    def _edit_template(self, group_type):
        return lookup_group_plugin(group_type).edit_template()

    def _activity_template(self, group_type):
        return lookup_group_plugin(group_type).activity_template()

    def _admins_template(self, group_type):
        return lookup_group_plugin(group_type).admins_template()

    def _bulk_process_template(self, group_type):
        return lookup_group_plugin(group_type).bulk_process_template()

    ## end hooks
    def _replace_group_org(self, string):
        ''' substitute organization for group if this is an org'''
        if self.group_type == 'organization':
            string = re.sub('^group', 'organization', string)
        return string

    def _action(self, action_name):
        ''' select the correct group/org action '''
        return get_action(self._replace_group_org(action_name))

    def _check_access(self, action_name, *args, **kw):
        ''' select the correct group/org check_access '''
        return check_access(self._replace_group_org(action_name), *args, **kw)

    def _render_template(self, template_name):
        ''' render the correct group/org template '''
        return render(self._replace_group_org(template_name))

    def _redirect_to(self, *args, **kw):
        ''' wrapper to ensue the correct controller is used '''
        if self.group_type == 'organization' and 'controller' in kw:
            kw['controller'] = 'organization'
        return h.redirect_to(*args, **kw)

    def _url_for(self, *args, **kw):
        ''' wrapper to ensue the correct controller is used '''
        if self.group_type == 'organization' and 'controller' in kw:
            kw['controller'] = 'organization'
        return h.url_for(*args, **kw)

    def _guess_group_type(self, expecting_name=False):
        """
            Guess the type of group from the URL handling the case
            where there is a prefix on the URL (such as /data/organization)
        """
        parts = [x for x in request.path.split('/') if x]

        idx = -1
        if expecting_name:
            idx = -2

        gt = parts[idx]
        if gt == 'group':
            gt = None

        return gt

    def index(self):
        group_type = self._guess_group_type()

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True,
                   'with_private': False}

        q = c.q = request.params.get('q', '')
        data_dict = {'all_fields': True, 'q': q}
        sort_by = c.sort_by_selected = request.params.get('sort')
        if sort_by:
            data_dict['sort'] = sort_by
        try:
            self._check_access('site_read', context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        # pass user info to context as needed to view private datasets of
        # orgs correctly
        if c.userobj:
            context['user_id'] = c.userobj.id
            context['user_is_admin'] = c.userobj.sysadmin

        results = self._action('group_list')(context, data_dict)

        c.page = h.Page(
            collection=results,
            page=request.params.get('page', 1),
            url=h.pager_url,
            items_per_page=21
        )
        return render(self._index_template(group_type))

    def read(self, id, limit=20):
        group_type = self._get_group_type(id.split('@')[0])
        if group_type != self.group_type:
            abort(404, _('Incorrect group type'))

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self._db_to_form_schema(group_type=group_type),
                   'for_view': True}
        data_dict = {'id': id}

        # unicode format (decoded from utf8)
        q = c.q = request.params.get('q', '')

        try:
            # Do not query for the group datasets when dictizing, as they will
            # be ignored and get requested on the controller anyway
            context['include_datasets'] = False
            c.group_dict = self._action('group_show')(context, data_dict)
            c.group = context['group']
        except NotFound:
            abort(404, _('Group not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % id)

        self._read(id, limit)
        return render(self._read_template(c.group_dict['type']))

    def _read(self, id, limit):
        ''' This is common code used by both read and bulk_process'''
        group_type = self._get_group_type(id.split('@')[0])
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self._db_to_form_schema(group_type=group_type),
                   'for_view': True, 'extras_as_string': True}

        q = c.q = request.params.get('q', '')
        # Search within group
        if c.group_dict.get('is_organization'):
            q += ' owner_org:"%s"' % c.group_dict.get('id')
        else:
            q += ' groups:"%s"' % c.group_dict.get('name')

        c.description_formatted = h.render_markdown(c.group_dict.get('description'))

        context['return_query'] = True

        # c.group_admins is used by CKAN's legacy (Genshi) templates only,
        # if we drop support for those then we can delete this line.
        c.group_admins = new_authz.get_group_or_org_admin_ids(c.group.id)

        try:
            page = int(request.params.get('page', 1))
        except ValueError, e:
            abort(400, ('"page" parameter must be an integer'))

        # most search operations should reset the page counter:
        params_nopage = [(k, v) for k, v in request.params.items()
                         if k != 'page']
        #sort_by = request.params.get('sort', 'name asc')
        sort_by = request.params.get('sort', None)

        def search_url(params):
            if group_type == 'organization':
                if c.action == 'bulk_process':
                    url = self._url_for(controller='organization',
                                        action='bulk_process',
                                        id=id)
                else:
                    url = self._url_for(controller='organization',
                                        action='read',
                                        id=id)
            else:
                url = self._url_for(controller='group', action='read', id=id)
            params = [(k, v.encode('utf-8') if isinstance(v, basestring)
                       else str(v)) for k, v in params]
            return url + u'?' + urlencode(params)

        def drill_down_url(**by):
            return h.add_url_param(alternative_url=None,
                                   controller='group', action='read',
                                   extras=dict(id=c.group_dict.get('name')),
                                   new_params=by)

        c.drill_down_url = drill_down_url

        def remove_field(key, value=None, replace=None):
            return h.remove_url_param(key, value=value, replace=replace,
                                      controller='group', action='read',
                                      extras=dict(id=c.group_dict.get('name')))

        c.remove_field = remove_field

        def pager_url(q=None, page=None):
            params = list(params_nopage)
            params.append(('page', page))
            return search_url(params)

        try:
            c.fields = []
            search_extras = {}
            for (param, value) in request.params.items():
                if not param in ['q', 'page', 'sort'] \
                        and len(value) and not param.startswith('_'):
                    if not param.startswith('ext_'):
                        c.fields.append((param, value))
                        q += ' %s: "%s"' % (param, value)
                    else:
                        search_extras[param] = value

            fq = 'capacity:"public"'
            user_member_of_orgs = [org['id'] for org
                                   in h.organizations_available('read')]

            if (c.group and c.group.id in user_member_of_orgs):
                fq = ''
                context['ignore_capacity_check'] = True

            facets = OrderedDict()

            default_facet_titles = {'organization': _('Organizations'),
                                    'groups': _('Groups'),
                                    'tags': _('Tags'),
                                    'res_format': _('Formats'),
                                    'license_id': _('Licenses')}

            for facet in g.facets:
                if facet in default_facet_titles:
                    facets[facet] = default_facet_titles[facet]
                else:
                    facets[facet] = facet

            # Facet titles
            for plugin in plugins.PluginImplementations(plugins.IFacets):
                if self.group_type == 'organization':
                    facets = plugin.organization_facets(
                        facets, self.group_type, None)
                else:
                    facets = plugin.group_facets(
                        facets, self.group_type, None)

            if 'capacity' in facets and (self.group_type != 'organization' or
                                         not user_member_of_orgs):
                del facets['capacity']

            c.facet_titles = facets

            data_dict = {
                'q': q,
                'fq': fq,
                'facet.field': facets.keys(),
                'rows': limit,
                'sort': sort_by,
                'start': (page - 1) * limit,
                'extras': search_extras
            }

            query = get_action('package_search')(context, data_dict)

            c.page = h.Page(
                collection=query['results'],
                page=page,
                url=pager_url,
                item_count=query['count'],
                items_per_page=limit
            )

            c.group_dict['package_count'] = query['count']
            c.facets = query['facets']
            maintain.deprecate_context_item('facets',
                                            'Use `c.search_facets` instead.')

            c.search_facets = query['search_facets']
            c.search_facets_limits = {}
            for facet in c.facets.keys():
                limit = int(request.params.get('_%s_limit' % facet,
                                               g.facets_default_number))
                c.search_facets_limits[facet] = limit
            c.page.items = query['results']

            c.sort_by_selected = sort_by

        except search.SearchError, se:
            log.error('Group search error: %r', se.args)
            c.query_error = True
            c.facets = {}
            c.page = h.Page(collection=[])

        self._setup_template_variables(context, {'id':id},
            group_type=group_type)

    def bulk_process(self, id):
        ''' Allow bulk processing of datasets for an organization.  Make
        private/public or delete. For organization admins.'''

        group_type = self._get_group_type(id.split('@')[0])

        if group_type != 'organization':
            # FIXME: better error
            raise Exception('Must be an organization')

        # check we are org admin

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self._db_to_form_schema(group_type=group_type),
                   'for_view': True, 'extras_as_string': True}
        data_dict = {'id': id}

        try:
            # Do not query for the group datasets when dictizing, as they will
            # be ignored and get requested on the controller anyway
            context['include_datasets'] = False
            c.group_dict = self._action('group_show')(context, data_dict)
            c.group = context['group']
        except NotFound:
            abort(404, _('Group not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % id)

        #use different form names so that ie7 can be detected
        form_names = set(["bulk_action.public", "bulk_action.delete",
                          "bulk_action.private"])
        actions_in_form = set(request.params.keys())
        actions = form_names.intersection(actions_in_form)
        # If no action then just show the datasets
        if not actions:
            # unicode format (decoded from utf8)
            limit = 500
            self._read(id, limit)
            c.packages = c.page.items
            return render(self._bulk_process_template(group_type))

        #ie7 puts all buttons in form params but puts submitted one twice
        for key, value in dict(request.params.dict_of_lists()).items():
            if len(value) == 2:
                action = key.split('.')[-1]
                break
        else:
            #normal good browser form submission
            action = actions.pop().split('.')[-1]

        # process the action first find the datasets to perform the action on.
        # they are prefixed by dataset_ in the form data
        datasets = []
        for param in request.params:
            if param.startswith('dataset_'):
                datasets.append(param[8:])

        action_functions = {
            'private': 'bulk_update_private',
            'public': 'bulk_update_public',
            'delete': 'bulk_update_delete',
        }

        data_dict = {'datasets': datasets, 'org_id': c.group_dict['id']}

        try:
            get_action(action_functions[action])(context, data_dict)
        except NotAuthorized:
            abort(401, _('Not authorized to perform bulk update'))
        base.redirect(h.url_for(controller='organization',
                                action='bulk_process',
                                id=id))

    def new(self, data=None, errors=None, error_summary=None):
        group_type = self._guess_group_type(True)
        if data:
            data['type'] = group_type

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'save': 'save' in request.params,
                   'parent': request.params.get('parent', None)}
        try:
            self._check_access('group_create', context)
        except NotAuthorized:
            abort(401, _('Unauthorized to create a group'))

        if context['save'] and not data:
            return self._save_new(context, group_type)

        data = data or {}
        if not data.get('image_url', '').startswith('http'):
            data.pop('image_url', None)

        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors,
                'error_summary': error_summary, 'action': 'new'}

        self._setup_template_variables(context, data, group_type=group_type)
        c.form = render(self._group_form(group_type=group_type),
                        extra_vars=vars)
        return render(self._new_template(group_type))

    def edit(self, id, data=None, errors=None, error_summary=None):
        group_type = self._get_group_type(id.split('@')[0])
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'save': 'save' in request.params,
                   'for_edit': True,
                   'parent': request.params.get('parent', None)
                   }
        data_dict = {'id': id}

        if context['save'] and not data:
            return self._save_edit(id, context)

        try:
            old_data = self._action('group_show')(context, data_dict)
            c.grouptitle = old_data.get('title')
            c.groupname = old_data.get('name')
            data = data or old_data
        except NotFound:
            abort(404, _('Group not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % '')

        group = context.get("group")
        c.group = group
        c.group_dict = self._action('group_show')(context, data_dict)

        try:
            self._check_access('group_update', context)
        except NotAuthorized, e:
            abort(401, _('User %r not authorized to edit %s') % (c.user, id))

        errors = errors or {}
        vars = {'data': data, 'errors': errors,
                'error_summary': error_summary, 'action': 'edit'}

        self._setup_template_variables(context, data, group_type=group_type)
        c.form = render(self._group_form(group_type), extra_vars=vars)
        return render(self._edit_template(c.group.type))

    def _get_group_type(self, id):
        """
        Given the id of a group it determines the type of a group given
        a valid id/name for the group.
        """
        group = model.Group.get(id)
        if not group:
            return None
        return group.type

    def _save_new(self, context, group_type=None):
        try:
            data_dict = clean_dict(dict_fns.unflatten(
                tuplize_dict(parse_params(request.params))))
            data_dict['type'] = group_type or 'group'
            context['message'] = data_dict.get('log_message', '')
            data_dict['users'] = [{'name': c.user, 'capacity': 'admin'}]
            group = self._action('group_create')(context, data_dict)

            # Redirect to the appropriate _read route for the type of group
            h.redirect_to(group['type'] + '_read', id=group['name'])
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % '')
        except NotFound, e:
            abort(404, _('Group not found'))
        except dict_fns.DataError:
            abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.new(data_dict, errors, error_summary)

    def _force_reindex(self, grp):
        ''' When the group name has changed, we need to force a reindex
        of the datasets within the group, otherwise they will stop
        appearing on the read page for the group (as they're connected via
        the group name)'''
        group = model.Group.get(grp['name'])
        for dataset in group.packages():
            search.rebuild(dataset.name)

    def _save_edit(self, id, context):
        try:
            data_dict = clean_dict(dict_fns.unflatten(
                tuplize_dict(parse_params(request.params))))
            context['message'] = data_dict.get('log_message', '')
            data_dict['id'] = id
            context['allow_partial_update'] = True
            group = self._action('group_update')(context, data_dict)
            if id != group['name']:
                self._force_reindex(group)

            h.redirect_to('%s_read' % group['type'], id=group['name'])
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % id)
        except NotFound, e:
            abort(404, _('Group not found'))
        except dict_fns.DataError:
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

        try:
            context = \
                {'model': model, 'user': c.user or c.author, 'group': group}
            self._check_access('group_edit_permissions', context)
            c.authz_editable = True
            c.group = context['group']
        except NotAuthorized:
            c.authz_editable = False
        if not c.authz_editable:
            abort(401,
                  _('User %r not authorized to edit %s authorizations') %
                   (c.user, id))

        roles = self._handle_update_of_authz(group)
        self._prepare_authz_info_for_render(roles)
        return render('group/authz.html')

    def delete(self, id):
        if 'cancel' in request.params:
            self._redirect_to(controller='group', action='edit', id=id)

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}

        try:
            self._check_access('group_delete', context, {'id': id})
        except NotAuthorized:
            abort(401, _('Unauthorized to delete group %s') % '')

        try:
            if request.method == 'POST':
                self._action('group_delete')(context, {'id': id})
                if self.group_type == 'organization':
                    h.flash_notice(_('Organization has been deleted.'))
                else:
                    h.flash_notice(_('Group has been deleted.'))
                self._redirect_to(controller='group', action='index')
            c.group_dict = self._action('group_show')(context, {'id': id})
        except NotAuthorized:
            abort(401, _('Unauthorized to delete group %s') % '')
        except NotFound:
            abort(404, _('Group not found'))
        return self._render_template('group/confirm_delete.html')

    def members(self, id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}

        try:
            c.members = self._action('member_list')(
                context, {'id': id, 'object_type': 'user'}
            )
            c.group_dict = self._action('group_show')(context, {'id': id})
        except NotAuthorized:
            abort(401, _('Unauthorized to delete group %s') % '')
        except NotFound:
            abort(404, _('Group not found'))
        return self._render_template('group/members.html')

    def member_new(self, id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}

        #self._check_access('group_delete', context, {'id': id})
        try:
            if request.method == 'POST':
                data_dict = clean_dict(dict_fns.unflatten(
                    tuplize_dict(parse_params(request.params))))
                data_dict['id'] = id

                email = data_dict.get('email')
                if email:
                    user_data_dict = {
                        'email': email,
                        'group_id': data_dict['id'],
                        'role': data_dict['role']
                    }
                    del data_dict['email']
                    user_dict = self._action('user_invite')(context,
                            user_data_dict)
                    data_dict['username'] = user_dict['name']

                c.group_dict = self._action('group_member_create')(context, data_dict)
                self._redirect_to(controller='group', action='members', id=id)
            else:
                user = request.params.get('user')
                if user:
                    c.user_dict = get_action('user_show')(context, {'id': user})
                    c.user_role = new_authz.users_role_for_group_or_org(id, user) or 'member'
                else:
                    c.user_role = 'member'
                c.group_dict = self._action('group_show')(context, {'id': id})
                group_type = 'organization' if c.group_dict['is_organization'] else 'group'
                c.roles = self._action('member_roles_list')(
                    context, {'group_type': group_type}
                )
        except NotAuthorized:
            abort(401, _('Unauthorized to add member to group %s') % '')
        except NotFound:
            abort(404, _('Group not found'))
        except ValidationError, e:
            h.flash_error(e.error_summary)
        return self._render_template('group/member_new.html')

    def member_delete(self, id):
        if 'cancel' in request.params:
            self._redirect_to(controller='group', action='members', id=id)

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}

        try:
            self._check_access('group_member_delete', context, {'id': id})
        except NotAuthorized:
            abort(401, _('Unauthorized to delete group %s members') % '')

        try:
            user_id = request.params.get('user')
            if request.method == 'POST':
                self._action('group_member_delete')(context, {'id': id, 'user_id': user_id})
                h.flash_notice(_('Group member has been deleted.'))
                self._redirect_to(controller='group', action='members', id=id)
            c.user_dict = self._action('user_show')(context, {'id': user_id})
            c.user_id = user_id
            c.group_id = id
        except NotAuthorized:
            abort(401, _('Unauthorized to delete group %s') % '')
        except NotFound:
            abort(404, _('Group not found'))
        return self._render_template('group/confirm_delete_member.html')

    def history(self, id):
        if 'diff' in request.params or 'selected1' in request.params:
            try:
                params = {'id': request.params.getone('group_name'),
                          'diff': request.params.getone('selected1'),
                          'oldid': request.params.getone('selected2'),
                          }
            except KeyError, e:
                if 'group_name' in dict(request.params):
                    id = request.params.getone('group_name')
                c.error = \
                    _('Select two revisions before doing the comparison.')
            else:
                params['diff_entity'] = 'group'
                h.redirect_to(controller='revision', action='diff', **params)

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self._db_to_form_schema()}
        data_dict = {'id': id}
        try:
            c.group_dict = self._action('group_show')(context, data_dict)
            c.group_revisions = self._action('group_revision_list')(context,
                                                                    data_dict)
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
                link=self._url_for(controller='group', action='read',
                                   id=c.group_dict['name']),
                description=_(u'Recent changes to CKAN Group: ') +
                c.group_dict['display_name'],
                language=unicode(get_lang()),
            )
            for revision_dict in c.group_revisions:
                revision_date = h.date_str_to_datetime(
                    revision_dict['timestamp'])
                try:
                    dayHorizon = int(request.params.get('days'))
                except:
                    dayHorizon = 30
                dayAge = (datetime.datetime.now() - revision_date).days
                if dayAge >= dayHorizon:
                    break
                if revision_dict['message']:
                    item_title = u'%s' % revision_dict['message'].\
                        split('\n')[0]
                else:
                    item_title = u'%s' % revision_dict['id']
                item_link = h.url_for(controller='revision', action='read',
                                      id=revision_dict['id'])
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
        return render(self._history_template(c.group_dict['type']))

    def activity(self, id, offset=0):
        '''Render this group's public activity stream page.'''

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}
        try:
            c.group_dict = self._get_group_dict(id)
        except NotFound:
            abort(404, _('Group not found'))
        except NotAuthorized:
            abort(401,
                  _('Unauthorized to read group {group_id}').format(
                      group_id=id))

        # Add the group's activity stream (already rendered to HTML) to the
        # template context for the group/read.html template to retrieve later.
        c.group_activity_stream = self._action('group_activity_list_html')(
            context, {'id': c.group_dict['id'], 'offset': offset})

        return render(self._activity_template(c.group_dict['type']))

    def follow(self, id):
        '''Start following this group.'''
        context = {'model': model,
                   'session': model.Session,
                   'user': c.user or c.author}
        data_dict = {'id': id}
        try:
            get_action('follow_group')(context, data_dict)
            group_dict = get_action('group_show')(context, data_dict)
            h.flash_success(_("You are now following {0}").format(
                group_dict['title']))
        except ValidationError as e:
            error_message = (e.extra_msg or e.message or e.error_summary
                             or e.error_dict)
            h.flash_error(error_message)
        except NotAuthorized as e:
            h.flash_error(e.extra_msg)
        h.redirect_to(controller='group', action='read', id=id)

    def unfollow(self, id):
        '''Stop following this group.'''
        context = {'model': model,
                   'session': model.Session,
                   'user': c.user or c.author}
        data_dict = {'id': id}
        try:
            get_action('unfollow_group')(context, data_dict)
            group_dict = get_action('group_show')(context, data_dict)
            h.flash_success(_("You are no longer following {0}").format(
                group_dict['title']))
        except ValidationError as e:
            error_message = (e.extra_msg or e.message or e.error_summary
                             or e.error_dict)
            h.flash_error(error_message)
        except (NotFound, NotAuthorized) as e:
            error_message = e.extra_msg or e.message
            h.flash_error(error_message)
        h.redirect_to(controller='group', action='read', id=id)

    def followers(self, id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}
        c.group_dict = self._get_group_dict(id)
        try:
            c.followers = get_action('group_follower_list')(context, {'id': id})
        except NotAuthorized:
            abort(401, _('Unauthorized to view followers %s') % '')
        return render('group/followers.html')

    def admins(self, id):
        c.group_dict = self._get_group_dict(id)
        c.admins = new_authz.get_group_or_org_admin_ids(id)
        return render(self._admins_template(c.group_dict['type']))

    def about(self, id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}
        c.group_dict = self._get_group_dict(id)
        group_type = c.group_dict['type']
        self._setup_template_variables(context, {'id': id},
                                       group_type=group_type)
        return render(self._about_template(group_type))

    def _get_group_dict(self, id):
        ''' returns the result of group_show action or aborts if there is a
        problem '''
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'for_view': True}
        try:
            return self._action('group_show')(context, {'id': id})
        except NotFound:
            abort(404, _('Group not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % id)

    def _render_edit_form(self, fs):
        # errors arrive in c.error and fs.errors
        c.fieldset = fs
        return render('group/edit_form.html')

    def _update(self, fs, group_name, group_id):
        '''
        Writes the POST data (associated with a group edit) to the database
        @input c.error
        '''
        validation = fs.validate()
        if not validation:
            c.form = self._render_edit_form(fs)
            raise base.ValidationException(fs)

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
            raise base.ValidationException(fs)
        try:
            fs.sync()
        except Exception, inst:
            model.Session.rollback()
            raise
        else:
            model.Session.commit()
