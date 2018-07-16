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

is_org = False


def _index_template(group_type):
    return lookup_group_plugin(group_type).index_template()


def _group_form(group_type=None):
    return lookup_group_plugin(group_type).group_form()


def _form_to_db_schema(group_type=None):
    return lookup_group_plugin(group_type).form_to_db_schema()


def _db_to_form_schema(group_type=None):
    u'''This is an interface to manipulate data from the database
     into a format suitable for the form (optional)'''
    return lookup_group_plugin(group_type).db_to_form_schema()


def _setup_template_variables(context, data_dict, group_type=None):
    if 'type' not in data_dict:
        data_dict['type'] = group_type
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


def _replace_group_org(string):
    u''' substitute organization for group if this is an org'''
    if is_org:
        return re.sub(u'^group', u'organization', string)
    return string


def _action(action_name):
    u''' select the correct group/org action '''
    return get_action(_replace_group_org(action_name))


def _check_access(action_name, *args, **kw):
    u''' select the correct group/org check_access '''
    return check_access(_replace_group_org(action_name), *args, **kw)


def _render_template(template_name, group_type):
    u''' render the correct group/org template '''
    return base.render(
        _replace_group_org(template_name),
        extra_vars={u'group_type': group_type})


def _force_reindex(grp):
    u''' When the group name has changed, we need to force a reindex
    of the datasets within the group, otherwise they will stop
    appearing on the read page for the group (as they're connected via
    the group name)'''
    group = model.Group.get(grp['name'])
    for dataset in group.packages():
        search.rebuild(dataset.name)


def _guess_group_type(expecting_name=False):
    u"""
            Guess the type of group from the URL.
            * The default url '/group/xyz' returns None
            * group_type is unicode
            * this handles the case where there is a prefix on the URL
              (such as /data/organization)
        """
    parts = [x for x in request.path.split(u'/') if x]

    idx = 0
    if expecting_name:
        idx = -1

    gt = parts[idx]

    return gt


def set_org(is_organization):
    global is_org
    is_org = is_organization


def index(group_type, is_organization):
    set_org(is_organization)
    page = h.get_page_number(request.params) or 1
    items_per_page = int(config.get(u'ckan.datasets_per_page', 20))

    context = {
        u'model': model,
        u'session': model.Session,
        u'user': c.user,
        u'for_view': True,
        u'with_private': False
    }

    try:
        _check_access(u'site_read', context)
        _check_access(u'group_list', context)
    except NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    q = c.q = request.params.get(u'q', u'')
    sort_by = c.sort_by_selected = request.params.get(u'sort')

    # pass user info to context as needed to view private datasets of
    # orgs correctly
    if c.userobj:
        context['user_id'] = c.userobj.id
        context['user_is_admin'] = c.userobj.sysadmin

    try:
        data_dict_global_results = {
            u'all_fields': False,
            u'q': q,
            u'sort': sort_by,
            u'type': group_type or u'group',
        }
        global_results = _action(u'group_list')(context,
                                                data_dict_global_results)
    except ValidationError as e:
        if e.error_dict and e.error_dict.get(u'message'):
            msg = e.error_dict['message']
        else:
            msg = str(e)
        h.flash_error(msg)
        c.page = h.Page([], 0)
        return base.render(
            _index_template(group_type),
            extra_vars={u'group_type': group_type})

    data_dict_page_results = {
        u'all_fields': True,
        u'q': q,
        u'sort': sort_by,
        u'type': group_type or u'group',
        u'limit': items_per_page,
        u'offset': items_per_page * (page - 1),
        u'include_extras': True
    }
    page_results = _action(u'group_list')(context, data_dict_page_results)

    c.page = h.Page(
        collection=global_results,
        page=page,
        url=h.pager_url,
        items_per_page=items_per_page, )

    c.page.items = page_results
    vars = dict(group_type=group_type)
    return base.render(_index_template(group_type), extra_vars=vars)


def _read(id, limit, group_type):
    u''' This is common code used by both read and bulk_process'''
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': c.user,
        u'schema': _db_to_form_schema(group_type=group_type),
        u'for_view': True,
        u'extras_as_string': True
    }

    q = c.q = request.params.get(u'q', u'')
    # Search within group
    if c.group_dict.get(u'is_organization'):
        fq = u' owner_org:"%s"' % c.group_dict.get(u'id')
    else:
        fq = u' groups:"%s"' % c.group_dict.get(u'name')

    c.description_formatted = \
        h.render_markdown(c.group_dict.get(u'description'))

    context['return_query'] = True

    page = h.get_page_number(request.params)

    # most search operations should reset the page counter:
    params_nopage = [(k, v) for k, v in request.params.items() if k != u'page']
    sort_by = request.params.get(u'sort', None)

    def search_url(params):
        controller = lookup_group_controller(group_type)
        action = u'bulk_process' if getattr(
            c, u'action', u'') == u'bulk_process' else u'read'
        url = h.url_for(u'.'.join([controller, action]), id=id)
        params = [(k, v.encode(u'utf-8')
                   if isinstance(v, basestring) else str(v))
                  for k, v in params]
        return url + u'?' + urlencode(params)

    def drill_down_url(**by):
        return h.add_url_param(
            alternative_url=None,
            controller=u'group',
            action=u'read',
            extras=dict(id=c.group_dict.get(u'name')),
            new_params=by)

    c.drill_down_url = drill_down_url

    def remove_field(key, value=None, replace=None):
        controller = lookup_group_controller(group_type)
        return h.remove_url_param(
            key,
            value=value,
            replace=replace,
            controller=controller,
            action=u'read',
            extras=dict(id=c.group_dict.get(u'name')))

    c.remove_field = remove_field

    def pager_url(q=None, page=None):
        params = list(params_nopage)
        params.append((u'page', page))
        return search_url(params)

    try:
        c.fields = []
        c.fields_grouped = {}
        search_extras = {}
        for (param, value) in request.params.items():
            if param not in [u'q', u'page', u'sort'] \
                    and len(value) and not param.startswith(u'_'):
                if not param.startswith(u'ext_'):
                    c.fields.append((param, value))
                    q += u' %s: "%s"' % (param, value)
                    if param not in c.fields_grouped:
                        c.fields_grouped[param] = [value]
                    else:
                        c.fields_grouped[param].append(value)
                else:
                    search_extras[param] = value

        facets = OrderedDict()

        default_facet_titles = {
            u'organization': _(u'Organizations'),
            u'groups': _(u'Groups'),
            u'tags': _(u'Tags'),
            u'res_format': _(u'Formats'),
            u'license_id': _(u'Licenses')
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
            u'q': q,
            u'fq': fq,
            u'include_private': True,
            u'facet.field': facets.keys(),
            u'rows': limit,
            u'sort': sort_by,
            u'start': (page - 1) * limit,
            u'extras': search_extras
        }

        context_ = dict((k, v) for (k, v) in context.items() if k != u'schema')
        query = get_action(u'package_search')(context_, data_dict)

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
                request.params.get(u'_%s_limit' % facet,
                                   config.get(u'search.facets.default', 10)))
            c.search_facets_limits[facet] = limit
        c.page.items = query['results']

        c.sort_by_selected = sort_by

    except search.SearchError, se:
        log.error(u'Group search error: %r', se.args)
        c.query_error = True
        c.page = h.Page(collection=[])

    _setup_template_variables(context, {u'id': id}, group_type=group_type)


def _update_facet_titles(facets, group_type):
    for plugin in plugins.PluginImplementations(plugins.IFacets):
        facets = plugin.group_facets(facets, group_type, None)


def _get_group_dict(id, group_type):
    u''' returns the result of group_show action or aborts if there is a
    problem '''
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': c.user,
        u'for_view': True
    }
    try:
        return _action(u'group_show')(context, {
            u'id': id,
            u'include_datasets': False
        })
    except (NotFound, NotAuthorized):
        base.abort(404, _(u'Group not found'))


def _redirect_to_this_controller(*args, **kw):
    u''' wrapper around redirect_to but it adds in this request's controller
    (so that it works for Organization or other derived controllers)'''
    kw['controller'] = request.endpoint.split(u'.')[0]
    return h.redirect_to(*args, **kw)


def _url_for_this_controller(*args, **kw):
    u''' wrapper around url_for but it adds in this request's controller
    (so that it works for Organization or other derived controllers)'''
    kw['controller'] = request.endpoint.split(u'.')[0]
    return h.url_for(*args, **kw)


def read(group_type, is_organization, id=None, limit=20):
    set_org(is_organization)
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': c.user,
        u'schema': _db_to_form_schema(group_type=group_type),
        u'for_view': True
    }
    data_dict = {u'id': id, u'type': group_type}

    # unicode format (decoded from utf8)
    c.q = request.params.get(u'q', u'')

    try:
        # Do not query for the group datasets when dictizing, as they will
        # be ignored and get requested on the controller anyway
        data_dict['include_datasets'] = False
        c.group_dict = _action(u'group_show')(context, data_dict)
        c.group = context['group']
    except (NotFound, NotAuthorized):
        base.abort(404, _(u'Group not found'))

    # if the user specified a group id, redirect to the group name
    if data_dict['id'] == c.group_dict['id'] and \
            data_dict['id'] != c.group_dict['name']:
        return h.redirect_to(u'{}.read'.format(group_type),
                             id=c.group_dict['name'])

    _read(id, limit, group_type)
    return base.render(
        _read_template(c.group_dict['type']),
        extra_vars={u'group_type': group_type})


def activity(id, group_type, is_organization, offset=0):
    u'''Render this group's public activity stream page.'''
    set_org(is_organization)
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': c.user,
        u'for_view': True
    }
    try:
        c.group_dict = _get_group_dict(id, group_type)
    except (NotFound, NotAuthorized):
        base.abort(404, _(u'Group not found'))

    try:
        # Add the group's activity stream (already rendered to HTML) to the
        # template context for the group/read.html
        # template to retrieve later.
        c.group_activity_stream = _action(u'group_activity_list_html')(
            context, {
                u'id': c.group_dict['id'],
                u'offset': offset
            })

    except ValidationError as error:
        base.abort(400, error.message)

    return base.render(
        _activity_template(group_type), extra_vars={u'group_type': group_type})


def about(id, group_type, is_organization):
    set_org(is_organization)
    context = {u'model': model, u'session': model.Session, u'user': c.user}
    c.group_dict = _get_group_dict(id, group_type)
    group_type = c.group_dict['type']
    _setup_template_variables(context, {u'id': id}, group_type=group_type)
    return base.render(
        _about_template(group_type), extra_vars={u'group_type': group_type})


def members(id, group_type, is_organization):
    set_org(is_organization)
    group_type = _guess_group_type()

    context = {u'model': model, u'session': model.Session, u'user': c.user}

    try:
        data_dict = {u'id': id}
        _check_access(u'group_edit_permissions', context, data_dict)
        c.members = get_action(u'member_list')(context, {
            u'id': id,
            u'object_type': u'user'
        })
        data_dict['include_datasets'] = False
        c.group_dict = _action(u'group_show')(context, data_dict)
    except NotFound:
        base.abort(404, _(u'Group not found'))
    except NotAuthorized:
        base.abort(403,
                   _(u'User %r not authorized to edit members of %s') %
                   (c.user, id))

    return _render_template(u'group/members.html', group_type)


def member_delete(id, group_type, is_organization):
    set_org(is_organization)
    if u'cancel' in request.params:
        return _redirect_to_this_controller(action=u'members', id=id)

    context = {u'model': model, u'session': model.Session, u'user': c.user}

    try:
        _check_access(u'group_member_delete', context, {u'id': id})
    except NotAuthorized:
        base.abort(403, _(u'Unauthorized to delete group %s members') % u'')

    try:
        user_id = request.params.get(u'user')
        if request.method == u'POST':
            _action(u'group_member_delete')(context, {
                u'id': id,
                u'user_id': user_id
            })
            h.flash_notice(_(u'Group member has been deleted.'))
            return _redirect_to_this_controller(action=u'members', id=id)
        c.user_dict = _action(u'group_show')(context, {u'id': user_id})
        c.user_id = user_id
        c.group_id = id
    except NotAuthorized:
        base.abort(403, _(u'Unauthorized to delete group %s members') % u'')
    except NotFound:
        base.abort(404, _(u'Group not found'))
    return _render_template(u'group/confirm_delete_member.html', group_type)


def history(id, group_type, is_organization):
    set_org(is_organization)
    if u'diff' in request.params or u'selected1' in request.params:
        try:
            params = {
                u'id': request.params.getone(u'group_name'),
                u'diff': request.params.getone(u'selected1'),
                u'oldid': request.params.getone(u'selected2'),
            }
        except KeyError:
            if u'group_name' in dict(request.params):
                id = request.params.getone(u'group_name')
            c.error = \
                _(u'Select two revisions before doing the comparison.')
        else:
            params[u'diff_entity'] = u'group'
            return h.redirect_to(controller=u'revision',
                                 action=u'diff', **params)

    context = {
        u'model': model,
        u'session': model.Session,
        u'user': c.user,
        u'schema': _db_to_form_schema()
    }
    data_dict = {u'id': id}
    try:
        c.group_dict = _action(u'group_show')(context, data_dict)
        c.group_revisions = _action(u'group_revision_list')(context, data_dict)
        # TODO: remove
        # Still necessary for the authz check in group/layout.html
        c.group = context['group']
    except (NotFound, NotAuthorized):
        base.abort(404, _(u'Group not found'))

    format = request.params.get(u'format', u'')
    if format == u'atom':
        # Generate and return Atom 1.0 document.
        from webhelpers.feedgenerator import Atom1Feed
        feed = Atom1Feed(
            title=_(u'CKAN Group Revision History'),
            link=_url_for_this_controller(
                action=u'read', id=c.group_dict['name']),
            description=_(u'Recent changes to CKAN Group: ') +
            c.group_dict['display_name'],
            language=unicode(get_lang()), )
        for revision_dict in c.group_revisions:
            revision_date = h.date_str_to_datetime(revision_dict['timestamp'])
            try:
                dayHorizon = int(request.params.get(u'days'))
            except:
                dayHorizon = 30
            dayAge = (datetime.datetime.now() - revision_date).days
            if dayAge >= dayHorizon:
                break
            if revision_dict['message']:
                item_title = u'%s' % revision_dict['message'].\
                    split(u'\n')[0]
            else:
                item_title = u'%s' % revision_dict['id']
            item_link = h.url_for(
                controller=u'revision', action=u'read', id=revision_dict['id'])
            item_description = _(u'Log message: ')
            item_description += u'%s' % (revision_dict['message'] or u'')
            item_author_name = revision_dict['author']
            item_pubdate = revision_date
            feed.add_item(
                title=item_title,
                link=item_link,
                description=item_description,
                author_name=item_author_name,
                pubdate=item_pubdate, )
        feed.content_type = u'application/atom+xml'
        return feed.writeString(u'utf-8')
    return base.render(
        _history_template(group_type), extra_vars={u'group_type': group_type})


def follow(id, group_type, is_organization):
    u'''Start following this group.'''
    set_org(is_organization)
    context = {u'model': model, u'session': model.Session, u'user': c.user}
    data_dict = {u'id': id}
    try:
        get_action(u'follow_group')(context, data_dict)
        group_dict = get_action(u'group_show')(context, data_dict)
        h.flash_success(
            _(u"You are now following {0}").format(group_dict['title']))

        id = group_dict['name']
    except ValidationError as e:
        error_message = (e.message or e.error_summary or e.error_dict)
        h.flash_error(error_message)
    except NotAuthorized as e:
        h.flash_error(e.message)
    return h.redirect_to(u'group.read', id=id)


def unfollow(id, group_type, is_organization):
    u'''Stop following this group.'''
    set_org(is_organization)
    context = {u'model': model, u'session': model.Session, u'user': c.user}
    data_dict = {u'id': id}
    try:
        get_action(u'unfollow_group')(context, data_dict)
        group_dict = get_action(u'group_show')(context, data_dict)
        h.flash_success(
            _(u"You are no longer following {0}").format(group_dict['title']))
        id = group_dict['name']
    except ValidationError as e:
        error_message = (e.message or e.error_summary or e.error_dict)
        h.flash_error(error_message)
    except (NotFound, NotAuthorized) as e:
        error_message = e.message
        h.flash_error(error_message)
    return h.redirect_to(u'group.read', id=id)


def followers(id, group_type, is_organization):
    set_org(is_organization)
    context = {u'model': model, u'session': model.Session, u'user': c.user}
    c.group_dict = _get_group_dict(id, group_type)
    try:
        c.followers = \
            get_action(u'group_follower_list')(context, {u'id': id})
    except NotAuthorized:
        base.abort(403, _(u'Unauthorized to view followers %s') % u'')
    return base.render(
        u'group/followers.html', extra_vars={u'group_type': group_type})


def admins(id, group_type, is_organization):
    set_org(is_organization)
    c.group_dict = _get_group_dict(id, group_type)
    c.admins = authz.get_group_or_org_admin_ids(id)
    return base.render(
        _admins_template(c.group_dict['type']),
        extra_vars={u'group_type': group_type})


class BulkProcessView(MethodView):
    u''' Bulk process view'''

    def _prepare(self, group_type, id=None):

        # check we are org admin

        context = {
            u'model': model,
            u'session': model.Session,
            u'user': c.user,
            u'schema': _db_to_form_schema(group_type=group_type),
            u'for_view': True,
            u'extras_as_string': True
        }
        return context

    def get(self, id, group_type, is_organization):
        set_org(is_organization)
        context = self._prepare(group_type, id)
        data_dict = {u'id': id, u'type': group_type}
        data_dict['include_datasets'] = False
        try:
            c.group_dict = _action(u'group_show')(context, data_dict)
            c.group = context['group']
        except NotFound:
            base.abort(404, _(u'Group not found'))

        if not c.group_dict['is_organization']:
            # FIXME: better error
            raise Exception(u'Must be an organization')

        # If no action then just show the datasets
        limit = 500
        _read(id, limit, group_type)
        c.packages = c.page.items

        return base.render(
            _bulk_process_template(group_type),
            extra_vars={u'group_type': group_type})

    def post(self, id, group_type, is_organization, data=None):
        set_org(is_organization)
        context = self._prepare(group_type)
        data_dict = {u'id': id, u'type': group_type}
        try:
            check_access(u'bulk_update_public', context, {u'org_id': id})
            # Do not query for the group datasets when dictizing, as they will
            # be ignored and get requested on the controller anyway
            data_dict['include_datasets'] = False
            c.group_dict = _action(u'group_show')(context, data_dict)
            c.group = context['group']
        except NotFound:
            base.abort(404, _(u'Group not found'))
        except NotAuthorized:
            base.abort(403,
                       _(u'User %r not authorized to edit %s') % (c.user, id))

        if not c.group_dict['is_organization']:
            # FIXME: better error
            raise Exception(u'Must be an organization')

        # use different form names so that ie7 can be detected
        form_names = set([
            u"bulk_action.public",
            u"bulk_action.delete",
            u"bulk_action.private"
        ])
        actions_in_form = set(request.form.keys())
        actions = form_names.intersection(actions_in_form)
        # ie7 puts all buttons in form params but puts submitted one twice

        for key, value in request.form.to_dict().iteritems():
            if value in [u'private', u'public']:
                action = key.split(u'.')[-1]
                break
        else:
            # normal good browser form submission
            action = actions.pop().split(u'.')[-1]

        # process the action first find the datasets to perform the action on.
        # they are prefixed by dataset_ in the form data
        datasets = []
        for param in request.form:
            if param.startswith(u'dataset_'):
                datasets.append(param[8:])

        action_functions = {
            u'private': u'bulk_update_private',
            u'public': u'bulk_update_public',
            u'delete': u'bulk_update_delete',
        }

        data_dict = {u'datasets': datasets, u'org_id': c.group_dict['id']}

        try:
            get_action(action_functions[action])(context, data_dict)
        except NotAuthorized:
            base.abort(403, _(u'Not authorized to perform bulk update'))
        return _redirect_to_this_controller(action=u'bulk_process', id=id)


class CreateGroupView(MethodView):
    u'''Create group view '''

    def _prepare(self, data=None):
        if data and u'type' in data:
            group_type = data['type']
        else:
            group_type = _guess_group_type()
        if data:
            data['type'] = group_type

        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'save': u'save' in request.params,
            u'parent': request.params.get(u'parent', None),
            u'group_type': group_type
        }

        try:
            _check_access(u'group_create', context)
        except NotAuthorized:
            base.abort(403, _(u'Unauthorized to create a group'))

        return context

    def post(self, group_type, is_organization):
        set_org(is_organization)
        context = self._prepare()
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form))))
            data_dict['type'] = group_type or u'group'
            context['message'] = data_dict.get(u'log_message', u'')
            data_dict['users'] = [{u'name': g.user, u'capacity': u'admin'}]
            group = _action(u'group_create')(context, data_dict)

        except (NotFound, NotAuthorized), e:
            base.abort(404, _(u'Group not found'))
        except dict_fns.DataError:
            base.abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(group_type, is_organization,
                            data_dict, errors, error_summary)

        return h.redirect_to(group['type'] + u'.read', id=group['name'])

    def get(self, group_type, is_organization,
            data=None, errors=None, error_summary=None):
        set_org(is_organization)
        context = self._prepare()
        data = data or {}
        if not data.get(u'image_url', u'').startswith(u'http'):
            data.pop(u'image_url', None)
        errors = errors or {}
        error_summary = error_summary or {}
        vars = {
            u'data': data,
            u'errors': errors,
            u'error_summary': error_summary,
            u'action': u'new',
            u'group_type': group_type
        }
        _setup_template_variables(
            context, data, group_type=group_type)
        c.form = base.render(
            _group_form(group_type=group_type), extra_vars=vars)
        return base.render(
            _new_template(group_type),
            extra_vars={u'group_type': group_type})


class EditGroupView(MethodView):
    u''' Edit group view'''

    def _prepare(self, id, is_organization, data=None):
        data_dict = {u'id': id, u'include_datasets': False}

        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'save': u'save' in request.params,
            u'for_edit': True,
            u'parent': request.params.get(u'parent', None),
            u'id': id
        }

        try:
            group = _action(u'group_show')(context, data_dict)
            check_access(u'group_update', context)
        except NotAuthorized:
            base.abort(403, _(u'Unauthorized to create a group'))
        except NotFound:
            base.abort(404, _(u'Group not found'))

        return context

    def post(self, group_type, is_organization, id=None):
        set_org(is_organization)
        context = self._prepare(id, is_organization)
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form))))
            context['message'] = data_dict.get(u'log_message', u'')
            data_dict['id'] = context['id']
            context['allow_partial_update'] = True
            group = _action(u'group_update')(context, data_dict)
            if id != group['name']:
                _force_reindex(group)

        except (NotFound, NotAuthorized), e:
            base.abort(404, _(u'Group not found'))
        except dict_fns.DataError:
            base.abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(id, group_type, is_organization,
                            data_dict, errors, error_summary)
        return h.redirect_to(group['type'] + u'.read', id=group['name'])

    def get(self, id, group_type, is_organization,
            data=None, errors=None, error_summary=None):
        set_org(is_organization)
        context = self._prepare(id, is_organization)
        data_dict = {u'id': id, u'include_datasets': False}
        try:
            data_dict['include_datasets'] = False
            old_data = context['group']
            c.grouptitle = old_data.get(u'title')
            c.groupname = old_data.get(u'name')
            data = data or old_data
        except (NotFound, NotAuthorized):
            base.abort(404, _(u'Group not found'))
        c.group_dict = data
        errors = errors or {}
        vars = {
            u'data': data,
            u'errors': errors,
            u'error_summary': error_summary,
            u'action': u'edit',
            u'group_type': group_type
        }

        _setup_template_variables(context, data, group_type=group_type)
        c.form = base.render(_group_form(group_type), extra_vars=vars)
        return base.render(
            _edit_template(group_type), extra_vars={u'group_type': group_type})


class DeleteGroupView(MethodView):
    u'''Delete group view '''

    def _prepare(self, id=None):
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': c.user,
        }
        try:
            _check_access(u'group_delete', context, {u'id': id})
        except NotAuthorized:
            base.abort(403, _(u'Unauthorized to delete group %s') % u'')
        return context

    def post(self, group_type, is_organization, id=None):
        set_org(is_organization)
        context = self._prepare(id)
        try:
            _action(u'group_delete')(context, {u'id': id})
            if group_type == u'organization':
                h.flash_notice(_(u'Organization has been deleted.'))
            elif group_type == u'group':
                h.flash_notice(_(u'Group has been deleted.'))
            else:
                h.flash_notice(
                    _(u'%s has been deleted.') % _(group_type.capitalize()))
            c.group_dict = _action(u'group_show')(context, {u'id': id})
        except NotAuthorized:
            base.abort(403, _(u'Unauthorized to delete group %s') % u'')
        except NotFound:
            base.abort(404, _(u'Group not found'))
        except ValidationError as e:
            h.flash_error(e.error_dict['message'])
            return h.redirect_to(u'organization.read', id=id)
        return _redirect_to_this_controller(action=u'index')

    def get(self, group_type, is_organization, id=None):
        set_org(is_organization)
        context = self._prepare(id)
        c.group_dict = _action(u'group_show')(context, {u'id': id})
        if u'cancel' in request.params:
            return _redirect_to_this_controller(action=u'edit', id=id)
        return _render_template(u'group/confirm_delete.html', group_type)


class MembersGroupView(MethodView):
    u'''New members group view'''

    def _prepare(self, id=None):
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': c.user
        }
        try:
            _check_access(u'group_member_create', context, {u'id': id})
        except NotAuthorized:
            base.abort(403,
                       _(u'Unauthorized to create group %s members') % u'')

        return context

    def post(self, group_type, is_organization, id=None):
        set_org(is_organization)
        context = self._prepare(id)
        data_dict = clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(request.form))))
        data_dict['id'] = id

        email = data_dict.get(u'email')

        if email:
            user_data_dict = {
                u'email': email,
                u'group_id': data_dict['id'],
                u'role': data_dict['role']
            }
            del data_dict['email']
            user_dict = _action(u'user_invite')(context, user_data_dict)
            data_dict['username'] = user_dict['name']

        try:
            c.group_dict = _action(u'group_member_create')(context, data_dict)
        except NotAuthorized:
            base.abort(403, _(u'Unauthorized to add member to group %s') % u'')
        except NotFound:
            base.abort(404, _(u'Group not found'))
        except ValidationError, e:
            h.flash_error(e.error_summary)

        return _redirect_to_this_controller(action=u'members', id=id)

    def get(self, group_type, is_organization, id=None):
        set_org(is_organization)
        context = self._prepare(id)
        user = request.params.get(u'user')
        data_dict = {u'id': id}
        data_dict['include_datasets'] = False
        c.group_dict = _action(u'group_show')(context, data_dict)
        c.roles = _action(u'member_roles_list')(context, {
            u'group_type': group_type
        })
        if user:
            c.user_dict = get_action(u'user_show')(context, {u'id': user})
            c.user_role =\
                authz.users_role_for_group_or_org(id, user) or u'member'
        else:
            c.user_role = u'member'
        return _render_template(u'group/member_new.html', group_type)


group = Blueprint(u'group', __name__, url_prefix=u'/group',
                  url_defaults={u'group_type': u'group',
                                u'is_organization': False})
organization = Blueprint(u'organization', __name__,
                         url_prefix=u'/organization',
                         url_defaults={u'group_type': u'organization',
                                       u'is_organization': True})


def register_group_plugin_rules(blueprint):
    actions = [
        u'member_delete', u'history', u'followers', u'follow',
        u'unfollow', u'admins', u'activity'
    ]
    blueprint.add_url_rule(u'/', view_func=index, strict_slashes=False)
    blueprint.add_url_rule(
        u'/new',
        methods=[u'GET', u'POST'],
        view_func=CreateGroupView.as_view(str(u'new')))
    blueprint.add_url_rule(u'/<id>', methods=[u'GET'], view_func=read)
    blueprint.add_url_rule(
        u'/edit/<id>', view_func=EditGroupView.as_view(str(u'edit')))
    blueprint.add_url_rule(
        u'/activity/<id>/<int:offset>', methods=[u'GET'], view_func=activity)
    blueprint.add_url_rule(u'/about/<id>', methods=[u'GET'], view_func=about)
    blueprint.add_url_rule(
        u'/members/<id>', methods=[u'GET', u'POST'], view_func=members)
    blueprint.add_url_rule(
        u'/member_new/<id>',
        view_func=MembersGroupView.as_view(str(u'member_new')))
    blueprint.add_url_rule(
        u'/bulk_process/<id>',
        view_func=BulkProcessView.as_view(str(u'bulk_process')))
    blueprint.add_url_rule(
        u'/delete/<id>',
        methods=[u'GET', u'POST'],
        view_func=DeleteGroupView.as_view(str(u'delete')))
    for action in actions:
        blueprint.add_url_rule(
            u'/{0}/<id>'.format(action),
            methods=[u'GET', u'POST'],
            view_func=globals()[action])


register_group_plugin_rules(group)
register_group_plugin_rules(organization)
