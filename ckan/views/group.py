# encoding: utf-8

import logging
import datetime
import re
from urllib import urlencode

from pylons.i18n import get_lang

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.lib.search as search
import ckan.model as model
import ckan.authz as authz
import ckan.lib.plugins as lib_plugins
import ckan.plugins as plugins
from ckan.common import OrderedDict, c, g, config, request, _
from flask import Blueprint
from flask.views import MethodView

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params

log = logging.getLogger(__name__)

lookup_group_plugin = lib_plugins.lookup_group_plugin
lookup_group_controller = lib_plugins.lookup_group_controller
lookup_group_blueprint = lib_plugins.lookup_group_blueprints

group = Blueprint('group', __name__, url_prefix=u'/group')
organization = Blueprint('organization', __name__, url_prefix=u'/organization')

group_types = ['group']


def _index_template(group_type):
    return lookup_group_plugin(group_type).index_template()


def _group_form(group_type=None):
    return lookup_group_plugin(group_type).group_form()


def _form_to_db_schema(group_type=None):
    return lookup_group_plugin(group_type).form_to_db_schema()


def _db_to_form_schema(group_type=None):
    '''This is an interface to manipulate data from the database
    into a format suitable for the form (optional)'''
    return lookup_group_plugin(group_type).db_to_form_schema()


def _setup_template_variables(context, data_dict, group_type=None):
    return lookup_group_plugin(group_type).\
        setup_template_variables(context, data_dict)


def _new_template(group_type):
    return lookup_group_plugin(group_type).new_template()


def _about_template(group_type):
    return lookup_group_plugin(group_type).about_template()


def _read_template(group_type):
    return lookup_group_plugin(group_type).read_template()


def _history_template(group_type):
    return lookup_group_plugin(group_type).history_template()


def _edit_template(group_type):
    return lookup_group_plugin(group_type).edit_template()


def _activity_template(group_type):
    return lookup_group_plugin(group_type).activity_template()


def _admins_template(group_type):
    return lookup_group_plugin(group_type).admins_template()


def _bulk_process_template(group_type):
    return lookup_group_plugin(group_type).bulk_process_template()


# end hooks


def _replace_group_org(string):
    ''' substitute organization for group if this is an org'''
    return re.sub('^group',
                  lookup_group_controller(_guess_group_type()), string)


def _action(action_name):
    ''' select the correct group/org action '''
    return get_action(_replace_group_org(action_name))


def _check_access(action_name, *args, **kw):
    ''' select the correct group/org check_access '''
    return check_access(_replace_group_org(action_name), *args, **kw)


def _render_template(template_name, group_type):
    ''' render the correct group/org template '''
    return base.render(
        _replace_group_org(template_name),
        extra_vars={'group_type': group_type})


def _force_reindex(grp):
    ''' When the group name has changed, we need to force a reindex
    of the datasets within the group, otherwise they will stop
    appearing on the read page for the group (as they're connected via
    the group name)'''
    group = model.Group.get(grp['name'])
    for dataset in group.packages():
        search.rebuild(dataset.name)


def _guess_group_type(expecting_name=False):
    """
            Guess the type of group from the URL.
            * The default url '/group/xyz' returns None
            * group_type is unicode
            * this handles the case where there is a prefix on the URL
              (such as /data/organization)
        """
    parts = [x for x in request.path.split('/') if x]

    idx = 0
    if expecting_name:
        idx = -1

    gt = parts[idx]

    return gt


def add_group_type(group_type):
    group_types.append(group_type)


def index():
    group_type = _guess_group_type()
    page = h.get_page_number(request.params) or 1
    items_per_page = int(config.get('ckan.datasets_per_page', 20))

    context = {
        'model': model,
        'session': model.Session,
        'user': c.user,
        'for_view': True,
        'with_private': False
    }

    try:
        _check_access('site_read', context)
        _check_access('group_list', context)
    except NotAuthorized:
        base.abort(403, _('Not authorized to see this page'))

    q = c.q = request.params.get('q', '')
    sort_by = c.sort_by_selected = request.params.get('sort')

    # pass user info to context as needed to view private datasets of
    # orgs correctly
    if c.userobj:
        context['user_id'] = c.userobj.id
        context['user_is_admin'] = c.userobj.sysadmin

    try:
        data_dict_global_results = {
            'all_fields': False,
            'q': q,
            'sort': sort_by,
            'type': group_type or 'group',
        }
        global_results = _action('group_list')(context,
                                               data_dict_global_results)
    except ValidationError as e:
        if e.error_dict and e.error_dict.get('message'):
            msg = e.error_dict['message']
        else:
            msg = str(e)
        h.flash_error(msg)
        c.page = h.Page([], 0)
        return base.render(
            _index_template(group_type), extra_vars={'group_type': group_type})

    data_dict_page_results = {
        'all_fields': True,
        'q': q,
        'sort': sort_by,
        'type': group_type or 'group',
        'limit': items_per_page,
        'offset': items_per_page * (page - 1),
        'include_extras': True
    }
    page_results = _action('group_list')(context, data_dict_page_results)

    c.page = h.Page(
        collection=global_results,
        page=page,
        url=h.pager_url,
        items_per_page=items_per_page, )

    c.page.items = page_results
    vars = dict(group_type=group_type)
    return base.render(_index_template(group_type), extra_vars=vars)


def _read(id, limit, group_type):
    ''' This is common code used by both read and bulk_process'''
    context = {
        'model': model,
        'session': model.Session,
        'user': c.user,
        'schema': _db_to_form_schema(group_type=group_type),
        'for_view': True,
        'extras_as_string': True
    }

    q = c.q = request.params.get('q', '')
    # Search within group
    if c.group_dict.get('is_organization'):
        q += ' owner_org:"%s"' % c.group_dict.get('id')
    else:
        q += ' groups:"%s"' % c.group_dict.get('name')

    c.description_formatted = \
        h.render_markdown(c.group_dict.get('description'))

    context['return_query'] = True

    page = h.get_page_number(request.params)

    # most search operations should reset the page counter:
    params_nopage = [(k, v) for k, v in request.params.items() if k != 'page']
    sort_by = request.params.get('sort', None)

    def search_url(params):
        controller = lookup_group_controller(group_type)
        action = u'bulk_process' if getattr(
            c, u'action') == u'bulk_process' else 'read'
        url = h.url_for('.'.join([controller, action]), id=id)
        params = [(k, v.encode('utf-8')
                   if isinstance(v, basestring) else str(v))
                  for k, v in params]
        return url + u'?' + urlencode(params)

    def drill_down_url(**by):
        return h.add_url_param(
            alternative_url=None,
            controller='group',
            action='read',
            extras=dict(id=c.group_dict.get('name')),
            new_params=by)

    c.drill_down_url = drill_down_url

    def remove_field(key, value=None, replace=None):
        controller = lookup_group_controller(group_type)
        return h.remove_url_param(
            key,
            value=value,
            replace=replace,
            controller=controller,
            action='read',
            extras=dict(id=c.group_dict.get('name')))

    c.remove_field = remove_field

    def pager_url(q=None, page=None):
        params = list(params_nopage)
        params.append(('page', page))
        return search_url(params)

    try:
        c.fields = []
        c.fields_grouped = {}
        search_extras = {}
        for (param, value) in request.params.items():
            if param not in ['q', 'page', 'sort'] \
                    and len(value) and not param.startswith('_'):
                if not param.startswith('ext_'):
                    c.fields.append((param, value))
                    q += ' %s: "%s"' % (param, value)
                    if param not in c.fields_grouped:
                        c.fields_grouped[param] = [value]
                    else:
                        c.fields_grouped[param].append(value)
                else:
                    search_extras[param] = value

        facets = OrderedDict()

        default_facet_titles = {
            'organization': _('Organizations'),
            'groups': _('Groups'),
            'tags': _('Tags'),
            'res_format': _('Formats'),
            'license_id': _('Licenses')
        }

        for facet in h.facets():
            if facet in default_facet_titles:
                facets[facet] = default_facet_titles[facet]
            else:
                facets[facet] = facet

        # Facet titles
        _update_facet_titles(facets, group_type)

        c.facet_titles = facets

        data_dict = {
            'q': q,
            'fq': '',
            'include_private': True,
            'facet.field': facets.keys(),
            'rows': limit,
            'sort': sort_by,
            'start': (page - 1) * limit,
            'extras': search_extras
        }

        context_ = dict((k, v) for (k, v) in context.items() if k != 'schema')
        query = get_action('package_search')(context_, data_dict)

        c.page = h.Page(
            collection=query['results'],
            page=page,
            url=pager_url,
            item_count=query['count'],
            items_per_page=limit)

        c.group_dict['package_count'] = query['count']

        c.search_facets = query['search_facets']
        c.search_facets_limits = {}
        for facet in c.search_facets.keys():
            limit = int(
                request.params.get('_%s_limit' % facet,
                                   config.get('search.facets.default', 10)))
            c.search_facets_limits[facet] = limit
        c.page.items = query['results']

        c.sort_by_selected = sort_by

    except search.SearchError, se:
        log.error('Group search error: %r', se.args)
        c.query_error = True
        c.page = h.Page(collection=[])

    _setup_template_variables(context, {'id': id}, group_type=group_type)


def _update_facet_titles(facets, group_type):
    for plugin in plugins.PluginImplementations(plugins.IFacets):
        facets = plugin.group_facets(facets, group_type, None)


def _get_group_dict(id, group_type):
    ''' returns the result of group_show action or aborts if there is a
    problem '''
    context = {
        'model': model,
        'session': model.Session,
        'user': c.user,
        'for_view': True
    }
    try:
        return _action('group_show')(context, {
            'id': id,
            'include_datasets': False
        })
    except (NotFound, NotAuthorized):
        base.abort(404, _('Group not found'))


def _redirect_to_this_controller(*args, **kw):
    ''' wrapper around redirect_to but it adds in this request's controller
    (so that it works for Organization or other derived controllers)'''
    kw['controller'] = request.endpoint.split('.')[0]
    return h.redirect_to(*args, **kw)


def _url_for_this_controller(*args, **kw):
    ''' wrapper around url_for but it adds in this request's controller
    (so that it works for Organization or other derived controllers)'''
    kw['controller'] = request.endpoint.split('.')[0]
    return h.url_for(*args, **kw)


def read(id=None, limit=20):
    group_type = _guess_group_type()
    context = {
        'model': model,
        'session': model.Session,
        'user': c.user,
        'schema': _db_to_form_schema(group_type=group_type),
        'for_view': True
    }
    data_dict = {'id': id, 'type': group_type}

    # unicode format (decoded from utf8)
    c.q = request.params.get('q', '')

    try:
        # Do not query for the group datasets when dictizing, as they will
        # be ignored and get requested on the controller anyway
        data_dict['include_datasets'] = False
        action = group_type + '_show'
        c.group_dict = _action(action)(context, data_dict)
        c.group = context['group']
    except (NotFound, NotAuthorized):
        base.abort(404, _('Group not found'))

    _read(id, limit, group_type)
    return base.render(
        _read_template(c.group_dict['type']),
        extra_vars={'group_type': group_type})


def activity(id, offset=0):
    '''Render this group's public activity stream page.'''

    group_type = _guess_group_type()
    context = {
        'model': model,
        'session': model.Session,
        'user': c.user,
        'for_view': True
    }
    try:
        c.group_dict = _get_group_dict(id, group_type)
    except (NotFound, NotAuthorized):
        base.abort(404, _('Group not found'))

    try:
        # Add the group's activity stream (already rendered to HTML) to the
        # template context for the group/read.html
        # template to retrieve later.
        c.group_activity_stream = _action('group_activity_list_html')(
            context, {
                'id': c.group_dict['id'],
                'offset': offset
            })

    except ValidationError as error:
        base.abort(400, error.message)

    return base.render(
        _activity_template(group_type), extra_vars={'group_type': group_type})


def about(id):
    group_type = _guess_group_type()
    context = {'model': model, 'session': model.Session, 'user': c.user}
    c.group_dict = _get_group_dict(id, group_type)
    group_type = c.group_dict['type']
    _setup_template_variables(context, {'id': id}, group_type=group_type)
    return base.render(
        _about_template(group_type), extra_vars={'group_type': group_type})


def members(id):
    group_type = _guess_group_type()

    context = {'model': model, 'session': model.Session, 'user': c.user}

    try:
        data_dict = {'id': id}
        check_access('group_edit_permissions', context, data_dict)
        c.members = get_action('member_list')(context, {
            'id': id,
            'object_type': 'user'
        })
        data_dict['include_datasets'] = False
        c.group_dict = _action('group_show')(context, data_dict)
    except NotFound:
        base.abort(404, _('Group not found'))
    except NotAuthorized:
        base.abort(403,
                   _('User %r not authorized to edit members of %s') % (c.user,
                                                                        id))

    return _render_template('group/members.html', group_type)


def member_delete(id):
    group_type = _guess_group_type()

    if 'cancel' in request.params:
        return _redirect_to_this_controller(action='members', id=id)

    context = {'model': model, 'session': model.Session, 'user': c.user}

    try:
        _check_access('group_member_delete', context, {'id': id})
    except NotAuthorized:
        base.abort(403, _('Unauthorized to delete group %s members') % '')

    try:
        user_id = request.params.get('user')
        if request.method == 'POST':
            _action('group_member_delete')(context, {
                'id': id,
                'user_id': user_id
            })
            h.flash_notice(_('Group member has been deleted.'))
            return _redirect_to_this_controller(action='members', id=id)
        c.user_dict = _action('group_show')(context, {'id': user_id})
        c.user_id = user_id
        c.group_id = id
    except NotAuthorized:
        base.abort(403, _('Unauthorized to delete group %s members') % '')
    except NotFound:
        base.abort(404, _('Group not found'))
    return _render_template('group/confirm_delete_member.html', group_type)


def history(id):
    group_type = _guess_group_type()
    if 'diff' in request.params or 'selected1' in request.params:
        try:
            params = {
                'id': request.params.getone('group_name'),
                'diff': request.params.getone('selected1'),
                'oldid': request.params.getone('selected2'),
            }
        except KeyError:
            if 'group_name' in dict(request.params):
                id = request.params.getone('group_name')
            c.error = \
                _('Select two revisions before doing the comparison.')
        else:
            params['diff_entity'] = 'group'
            h.redirect_to(controller='revision', action='diff', **params)

    context = {
        'model': model,
        'session': model.Session,
        'user': c.user,
        'schema': _db_to_form_schema()
    }
    data_dict = {'id': id}
    try:
        c.group_dict = _action('group_show')(context, data_dict)
        c.group_revisions = _action('group_revision_list')(context, data_dict)
        # TODO: remove
        # Still necessary for the authz check in group/layout.html
        c.group = context['group']
    except (NotFound, NotAuthorized):
        base.abort(404, _('Group not found'))

    format = request.params.get('format', '')
    if format == 'atom':
        # Generate and return Atom 1.0 document.
        from webhelpers.feedgenerator import Atom1Feed
        feed = Atom1Feed(
            title=_(u'CKAN Group Revision History'),
            link=_url_for_this_controller(
                action='read', id=c.group_dict['name']),
            description=_(u'Recent changes to CKAN Group: ') +
            c.group_dict['display_name'],
            language=unicode(get_lang()), )
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
                item_title = u'%s' % revision_dict['message'].\
                    split('\n')[0]
            else:
                item_title = u'%s' % revision_dict['id']
            item_link = h.url_for(
                controller='revision', action='read', id=revision_dict['id'])
            item_description = _('Log message: ')
            item_description += '%s' % (revision_dict['message'] or '')
            item_author_name = revision_dict['author']
            item_pubdate = revision_date
            feed.add_item(
                title=item_title,
                link=item_link,
                description=item_description,
                author_name=item_author_name,
                pubdate=item_pubdate, )
        feed.content_type = 'application/atom+xml'
        return feed.writeString('utf-8')
    return base.render(
        _history_template(group_type), extra_vars={'group_type': group_type})


def follow(id):
    '''Start following this group.'''
    context = {'model': model, 'session': model.Session, 'user': c.user}
    data_dict = {'id': id}
    try:
        get_action('follow_group')(context, data_dict)
        group_dict = get_action('group_show')(context, data_dict)
        h.flash_success(
            _("You are now following {0}").format(group_dict['title']))
    except ValidationError as e:
        error_message = (e.message or e.error_summary or e.error_dict)
        h.flash_error(error_message)
    except NotAuthorized as e:
        h.flash_error(e.message)
    return h.redirect_to('group.read', id=id)


def unfollow(id):
    '''Stop following this group.'''
    context = {'model': model, 'session': model.Session, 'user': c.user}
    data_dict = {'id': id}
    try:
        get_action('unfollow_group')(context, data_dict)
        group_dict = get_action('group_show')(context, data_dict)
        h.flash_success(
            _("You are no longer following {0}").format(group_dict['title']))
    except ValidationError as e:
        error_message = (e.message or e.error_summary or e.error_dict)
        h.flash_error(error_message)
    except (NotFound, NotAuthorized) as e:
        error_message = e.message
        h.flash_error(error_message)
    return h.redirect_to('group.read', id=id)


def followers(id):
    group_type = _guess_group_type()
    context = {'model': model, 'session': model.Session, 'user': c.user}
    c.group_dict = _get_group_dict(id, group_type)
    try:
        c.followers = \
            get_action('group_follower_list')(context, {'id': id})
    except NotAuthorized:
        base.abort(403, _('Unauthorized to view followers %s') % '')
    return base.render(
        'group/followers.html', extra_vars={'group_type': group_type})


def admins(id):
    group_type = _guess_group_type()
    c.group_dict = _get_group_dict(id, group_type)
    c.admins = authz.get_group_or_org_admin_ids(id)
    return base.render(
        _admins_template(c.group_dict['type']),
        extra_vars={'group_type': group_type})


def bulk_process(id):
    ''' Allow bulk processing of datasets for an organization.  Make
        private/public or delete. For organization admins.'''

    group_type = _guess_group_type()

    # check we are org admin

    context = {
        'model': model,
        'session': model.Session,
        'user': c.user,
        'schema': _db_to_form_schema(group_type=group_type),
        'for_view': True,
        'extras_as_string': True
    }
    data_dict = {'id': id, 'type': group_type}

    try:
        check_access('bulk_update_public', context, {'org_id': id})
        # Do not query for the group datasets when dictizing, as they will
        # be ignored and get requested on the controller anyway
        data_dict['include_datasets'] = False
        c.group_dict = _action('group_show')(context, data_dict)
        c.group = context['group']
    except NotFound:
        base.abort(404, _('Group not found'))
    except NotAuthorized:
        base.abort(403, _('User %r not authorized to edit %s') % (c.user, id))

    if not c.group_dict['is_organization']:
        # FIXME: better error
        raise Exception('Must be an organization')

    # use different form names so that ie7 can be detected
    form_names = set(
        ["bulk_action.public", "bulk_action.delete", "bulk_action.private"])
    actions_in_form = set(request.params.keys())
    actions = form_names.intersection(actions_in_form)
    # If no action then just show the datasets
    if not actions:
        # unicode format (decoded from utf8)
        limit = 500
        _read(id, limit, group_type)
        c.packages = c.page.items
        return base.render(
            _bulk_process_template(group_type),
            extra_vars={'group_type': group_type})

    # ie7 puts all buttons in form params but puts submitted one twice
    for key, value in dict(request.params.dict_of_lists()).items():
        if len(value) == 2:
            action = key.split('.')[-1]
            break
    else:
        # normal good browser form submission
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
        base.abort(403, _('Not authorized to perform bulk update'))
    return _redirect_to_this_controller(action='bulk_process', id=id)


class BulkProcessView(MethodView):
    ''' Bulk process view'''

    def _prepare(self, id=None):
        group_type = _guess_group_type()

        # check we are org admin

        context = {
            'model': model,
            'session': model.Session,
            'user': c.user,
            'schema': _db_to_form_schema(group_type=group_type),
            'for_view': True,
            'extras_as_string': True,
            'group_type': group_type
        }
        return context

    def get(self, id):
        context = self._prepare(id)
        group_type = context['group_type']
        data_dict = {'id': id, 'type': group_type}
        data_dict['include_datasets'] = False
        try:
            c.group_dict = _action('group_show')(context, data_dict)
            c.group = context['group']
        except NotFound:
            base.abort(404, _('Group not found'))

        # If no action then just show the datasets
        limit = 500
        _read(id, limit, group_type)
        c.packages = c.page.items

        return base.render(
            _bulk_process_template(group_type),
            extra_vars={'group_type': group_type})

    def post(self, id, data=None):
        context = self._prepare()
        group_type = context['group_type']
        data_dict = {'id': id, 'type': group_type}
        try:
            check_access('bulk_update_public', context, {'org_id': id})
            # Do not query for the group datasets when dictizing, as they will
            # be ignored and get requested on the controller anyway
            data_dict['include_datasets'] = False
            c.group_dict = _action('group_show')(context, data_dict)
            c.group = context['group']
        except NotFound:
            base.abort(404, _('Group not found'))
        except NotAuthorized:
            base.abort(403,
                       _('User %r not authorized to edit %s') % (c.user, id))

        if not c.group_dict['is_organization']:
            # FIXME: better error
            raise Exception('Must be an organization')

        # use different form names so that ie7 can be detected
        form_names = set([
            "bulk_action.public", "bulk_action.delete", "bulk_action.private"
        ])
        actions_in_form = set(request.form.keys())
        actions = form_names.intersection(actions_in_form)
        # ie7 puts all buttons in form params but puts submitted one twice

        for key, value in request.form.to_dict().iteritems():
            if value in [u'private', u'public']:
                action = key.split('.')[-1]
                break
        else:
            # normal good browser form submission
            action = actions.pop().split('.')[-1]

        # process the action first find the datasets to perform the action on.
        # they are prefixed by dataset_ in the form data
        datasets = []
        for param in request.form:
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
            base.abort(403, _('Not authorized to perform bulk update'))
        return _redirect_to_this_controller(action='bulk_process', id=id)


class CreateGroupView(MethodView):
    '''Create group view '''

    def _prepare(self, data=None):
        if data and 'type' in data:
            group_type = data['type']
        else:
            group_type = _guess_group_type()
        if data:
            data['type'] = group_type

        context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
            'save': 'save' in request.params,
            'parent': request.params.get('parent', None),
            'group_type': group_type
        }

        try:
            action_create = group_type + '_create'
            check_access(action_create, context)
        except NotAuthorized:
            base.abort(403, _('Unauthorized to create a group'))

        return context

    def post(self):
        context = self._prepare()
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form))))
            data_dict['type'] = context['group_type'] or 'group'
            context['message'] = data_dict.get('log_message', '')
            data_dict['users'] = [{'name': g.user, 'capacity': 'admin'}]
            group = _action('group_create')(context, data_dict)

        except (NotFound, NotAuthorized), e:
            base.abort(404, _('Group not found'))
        except dict_fns.DataError:
            base.abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(data_dict, errors, error_summary)

        return h.redirect_to(group['type'] + '.read', id=group['name'])

    def get(self, data=None, errors=None, error_summary=None):
        context = self._prepare()

        data = data or {}
        if not data.get('image_url', '').startswith('http'):
            data.pop('image_url', None)
        errors = errors or {}
        error_summary = error_summary or {}
        vars = {
            'data': data,
            'errors': errors,
            'error_summary': error_summary,
            'action': 'new',
            'group_type': context['group_type']
        }
        _setup_template_variables(
            context, data, group_type=context['group_type'])
        c.form = base.render(
            _group_form(group_type=context['group_type']), extra_vars=vars)
        return base.render(
            _new_template(context['group_type']),
            extra_vars={'group_type': context['group_type']})


class EditGroupView(MethodView):
    ''' Edit group view'''

    def _prepare(self, id, data=None):
        if data and 'type' in data:
            group_type = data['type']
        else:
            group_type = _guess_group_type()
        if data:
            data['type'] = group_type
        data_dict = {'id': id, 'include_datasets': False}

        context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
            'save': 'save' in request.params,
            'for_edit': True,
            'parent': request.params.get('parent', None),
            'group_type': group_type,
            'id': id
        }

        try:
            group = _action('group_show')(context, data_dict)
            check_access(group_type + '_update', context)
        except NotAuthorized:
            base.abort(403, _('Unauthorized to create a group'))
        except NotFound:
            base.abort(404, _('Group not found'))

        return context

    def post(self, id=None):
        context = self._prepare(id)
        group_type = context['group_type']
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form))))
            context['message'] = data_dict.get('log_message', '')
            data_dict['id'] = context['id']
            context['allow_partial_update'] = True
            group = _action('group_update')(context, data_dict)
            if id != group['name']:
                _force_reindex(group)

        except (NotFound, NotAuthorized), e:
            base.abort(404, _('Group not found'))
        except dict_fns.DataError:
            base.abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(id, data_dict, errors, error_summary)
        return h.redirect_to(group['type'] + '.read', id=group['name'])

    def get(self, id, data=None, errors=None, error_summary=None):
        context = self._prepare(id)
        group_type = context['group_type']
        data_dict = {'id': id, 'include_datasets': False}
        try:
            data_dict['include_datasets'] = False
            old_data = context['group']
            c.grouptitle = old_data.get('title')
            c.groupname = old_data.get('name')
            data = data or old_data
        except (NotFound, NotAuthorized):
            base.abort(404, _('Group not found'))
        c.group_dict = data
        errors = errors or {}
        vars = {
            'data': data,
            'errors': errors,
            'error_summary': error_summary,
            'action': 'edit',
            'group_type': group_type
        }

        _setup_template_variables(context, data, group_type=group_type)
        c.form = base.render(_group_form(group_type), extra_vars=vars)
        return base.render(
            _edit_template(group_type), extra_vars={'group_type': group_type})


class DeleteGroupView(MethodView):
    '''Delete group view '''

    def _prepare(self, id=None):
        group_type = _guess_group_type()
        context = {
            'model': model,
            'session': model.Session,
            'user': c.user,
            'group_type': group_type
        }
        try:
            _check_access('group_delete', context, {'id': id})
        except NotAuthorized:
            base.abort(403, _('Unauthorized to delete group %s') % '')
        return context

    def post(self, id=None):
        context = self._prepare(id)
        group_type = context['group_type']
        try:
            _action('group_delete')(context, {'id': id})
            if group_type == 'organization':
                h.flash_notice(_('Organization has been deleted.'))
            elif group_type == 'group':
                h.flash_notice(_('Group has been deleted.'))
            else:
                h.flash_notice(
                    _('%s has been deleted.') % _(group_type.capitalize()))
            c.group_dict = _action('group_show')(context, {'id': id})
        except NotAuthorized:
            base.abort(403, _('Unauthorized to delete group %s') % '')
        except NotFound:
            base.abort(404, _('Group not found'))
        except ValidationError as e:
            h.flash_error(e.error_dict['message'])
            h.redirect_to('organization.read', id=id)
        return _redirect_to_this_controller(action='index')

    def get(self, id=None):
        context = self._prepare(id)
        group_type = context['group_type']
        c.group_dict = _action('group_show')(context, {'id': id})
        if 'cancel' in request.params:
            return _redirect_to_this_controller(action='edit', id=id)
        group_type = context['group_type']
        return _render_template('group/confirm_delete.html', group_type)


class MembersGroupView(MethodView):
    '''New members group view'''

    def _prepare(self, id=None):
        group_type = _guess_group_type()
        context = {
            'model': model,
            'session': model.Session,
            'user': c.user,
            'group_type': group_type
        }
        try:
            action = group_type + '_member_create'
            check_access(action, context, {'id': id})
        except NotAuthorized:
            base.abort(403, _('Unauthorized to create group %s members') % '')

        return context

    def post(self, id=None):
        context = self._prepare(id)
        group_type = context['group_type']
        data_dict = clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(request.form))))
        data_dict['id'] = id

        email = data_dict.get('email')

        if email:
            user_data_dict = {
                'email': email,
                'group_id': data_dict['id'],
                'role': data_dict['role']
            }
            del data_dict['email']
            user_dict = _action('user_invite')(context, user_data_dict)
            data_dict['username'] = user_dict['name']

        try:
            c.group_dict = _action('group_member_create')(context, data_dict)
        except NotAuthorized:
            base.abort(403, _('Unauthorized to add member to group %s') % '')
        except NotFound:
            base.abort(404, _('Group not found'))
        except ValidationError, e:
            h.flash_error(e.error_summary)

        return _redirect_to_this_controller(action='members', id=id)

    def get(self, id=None):
        context = self._prepare(id)
        group_type = context['group_type']
        user = request.params.get('user')
        data_dict = {'id': id}
        data_dict['include_datasets'] = False
        c.group_dict = _action('group_show')(context, data_dict)
        c.roles = _action('member_roles_list')(context, {
            'group_type': group_type
        })
        if user:
            c.user_dict = get_action('user_show')(context, {'id': user})
            c.user_role =\
                authz.users_role_for_group_or_org(id, user) or 'member'
        else:
            c.user_role = 'member'
        return _render_template('group/member_new.html', context['group_type'])


actions = [
    'member_delete', 'history', 'followers', 'follow', 'unfollow', 'admins',
    'activity'
]
# Routing for groups
group.add_url_rule(u'/', view_func=index, strict_slashes=False)
group.add_url_rule(
    u'/new',
    methods=[u'GET', u'POST'],
    view_func=CreateGroupView.as_view(str('new')))
group.add_url_rule(u'/<id>', methods=[u'GET'], view_func=read)
group.add_url_rule(u'/edit/<id>', view_func=EditGroupView.as_view(str('edit')))
group.add_url_rule(
    u'/activity/<id>/<int:offset>', methods=[u'GET'], view_func=activity)
group.add_url_rule(u'/about/<id>', methods=[u'GET'], view_func=about)
group.add_url_rule(
    u'/members/<id>', methods=[u'GET', u'POST'], view_func=members)
group.add_url_rule(
    u'/member_new/<id>', view_func=MembersGroupView.as_view(str('member_new')))
group.add_url_rule(
    u'/bulk_process/<id>',
    view_func=BulkProcessView.as_view(str('bulk_process')))
group.add_url_rule(
    u'/delete/<id>',
    methods=[u'GET', u'POST'],
    view_func=DeleteGroupView.as_view(str('delete')))
for action in actions:
    group.add_url_rule(
        u'/{0}/<id>'.format(action),
        methods=[u'GET', u'POST'],
        view_func=globals()[action])

# Routing for organizations
organization.add_url_rule(u'/', view_func=index, strict_slashes=False)
organization.add_url_rule(
    u'/new',
    methods=[u'GET', u'POST'],
    view_func=CreateGroupView.as_view(str('new')))
organization.add_url_rule(u'/<id>', methods=[u'GET'], view_func=read)
organization.add_url_rule(
    u'/edit/<id>', view_func=EditGroupView.as_view(str('edit')))
organization.add_url_rule(
    u'/activity/<id>/<int:offset>', methods=[u'GET'], view_func=activity)
organization.add_url_rule(u'/about/<id>', methods=[u'GET'], view_func=about)
organization.add_url_rule(
    u'/members/<id>', methods=[u'GET', u'POST'], view_func=members)
organization.add_url_rule(
    u'/member_new/<id>', view_func=MembersGroupView.as_view(str('member_new')))
organization.add_url_rule(
    u'/bulk_process/<id>',
    view_func=BulkProcessView.as_view(str('bulk_process')))
organization.add_url_rule(
    u'/delete/<id>',
    methods=[u'GET', u'POST'],
    view_func=DeleteGroupView.as_view(str('delete')))
for action in actions:
    organization.add_url_rule(
        u'/{0}/<id>'.format(action),
        methods=[u'GET', u'POST'],
        view_func=globals()[action])
