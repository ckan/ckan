# encoding: utf-8

import logging
import re
from collections import OrderedDict

import six
from six import string_types
from six.moves.urllib.parse import urlencode

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.lib.search as search
import ckan.model as model
import ckan.authz as authz
import ckan.lib.plugins as lib_plugins
import ckan.plugins as plugins
from ckan.common import g, config, request, _
from ckan.views.home import CACHE_PARAMETERS
from ckan.views.dataset import _get_search_details

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


def _get_group_template(template_type, group_type=None):
    group_plugin = lookup_group_plugin(group_type)
    method = getattr(group_plugin, template_type)
    try:
        return method(group_type)
    except TypeError as err:
        if u'takes 1' not in str(err) and u'takes exactly 1' not in str(err):
            raise
        return method()


def _db_to_form_schema(group_type=None):
    u'''This is an interface to manipulate data from the database
     into a format suitable for the form (optional)'''
    return lookup_group_plugin(group_type).db_to_form_schema()


def _setup_template_variables(context, data_dict, group_type=None):
    if u'type' not in data_dict:
        data_dict[u'type'] = group_type
    return lookup_group_plugin(group_type).\
        setup_template_variables(context, data_dict)


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
    extra_vars = {}
    set_org(is_organization)
    page = h.get_page_number(request.params) or 1
    items_per_page = int(config.get(u'ckan.datasets_per_page', 20))

    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'for_view': True,
        u'with_private': False
    }

    try:
        _check_access(u'site_read', context)
        _check_access(u'group_list', context)
    except NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    q = request.params.get(u'q', u'')
    sort_by = request.params.get(u'sort')

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.q = q
    g.sort_by_selected = sort_by

    extra_vars["q"] = q
    extra_vars["sort_by_selected"] = sort_by

    # pass user info to context as needed to view private datasets of
    # orgs correctly
    if g.userobj:
        context['user_id'] = g.userobj.id
        context['user_is_admin'] = g.userobj.sysadmin

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
        extra_vars["page"] = h.Page([], 0)
        extra_vars["group_type"] = group_type
        return base.render(
            _get_group_template(u'index_template', group_type), extra_vars)

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

    extra_vars["page"] = h.Page(
        collection=global_results,
        page=page,
        url=h.pager_url,
        items_per_page=items_per_page, )

    extra_vars["page"].items = page_results
    extra_vars["group_type"] = group_type

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.page = extra_vars["page"]
    return base.render(
        _get_group_template(u'index_template', group_type), extra_vars)


def _read(id, limit, group_type):
    u''' This is common code used by both read and bulk_process'''
    extra_vars = {}
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'schema': _db_to_form_schema(group_type=group_type),
        u'for_view': True,
        u'extras_as_string': True
    }

    q = request.params.get(u'q', u'')

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.q = q

    # Search within group
    if g.group_dict.get(u'is_organization'):
        fq = u' owner_org:"%s"' % g.group_dict.get(u'id')
    else:
        fq = u' groups:"%s"' % g.group_dict.get(u'name')

    extra_vars["q"] = q

    g.description_formatted = \
        h.render_markdown(g.group_dict.get(u'description'))

    context['return_query'] = True

    page = h.get_page_number(request.params)

    # most search operations should reset the page counter:
    params_nopage = [(k, v) for k, v in request.params.items() if k != u'page']
    sort_by = request.params.get(u'sort', None)

    def search_url(params):
        controller = lookup_group_controller(group_type)
        action = u'bulk_process' if getattr(
            g, u'action', u'') == u'bulk_process' else u'read'
        url = h.url_for(u'.'.join([controller, action]), id=id)
        params = [(k, v.encode(u'utf-8')
                   if isinstance(v, string_types) else str(v))
                  for k, v in params]
        return url + u'?' + urlencode(params)

    def drill_down_url(**by):
        return h.add_url_param(
            alternative_url=None,
            controller=group_type,
            action=u'read',
            extras=dict(id=g.group_dict.get(u'name')),
            new_params=by)

    extra_vars["drill_down_url"] = drill_down_url

    def remove_field(key, value=None, replace=None):
        controller = lookup_group_controller(group_type)
        return h.remove_url_param(
            key,
            value=value,
            replace=replace,
            controller=controller,
            action=u'read',
            extras=dict(id=g.group_dict.get(u'name')))

    extra_vars["remove_field"] = remove_field

    def pager_url(q=None, page=None):
        params = list(params_nopage)
        params.append((u'page', page))
        return search_url(params)

    details = _get_search_details()
    extra_vars[u'fields'] = details[u'fields']
    extra_vars[u'fields_grouped'] = details[u'fields_grouped']
    fq += details[u'fq']
    search_extras = details[u'search_extras']

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.fields = extra_vars[u'fields']
    g.fields_grouped = extra_vars[u'fields_grouped']

    facets = OrderedDict()

    org_label = h.humanize_entity_type(
        u'organization',
        h.default_group_type(u'organization'),
        u'facet label') or _(u'Organizations')

    group_label = h.humanize_entity_type(
        u'group',
        h.default_group_type(u'group'),
        u'facet label') or _(u'Groups')

    default_facet_titles = {
        u'organization': org_label,
        u'groups': group_label,
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
    facets = _update_facet_titles(facets, group_type)

    extra_vars["facet_titles"] = facets

    data_dict = {
        u'q': q,
        u'fq': fq,
        u'include_private': True,
        u'facet.field': list(facets.keys()),
        u'rows': limit,
        u'sort': sort_by,
        u'start': (page - 1) * limit,
        u'extras': search_extras
    }

    context_ = dict((k, v) for (k, v) in context.items() if k != u'schema')
    try:
        query = get_action(u'package_search')(context_, data_dict)
    except search.SearchError as se:
        log.error(u'Group search error: %r', se.args)
        extra_vars["query_error"] = True
        extra_vars["page"] = h.Page(collection=[])
    else:
        extra_vars["page"] = h.Page(
            collection=query['results'],
            page=page,
            url=pager_url,
            item_count=query['count'],
            items_per_page=limit)

        # TODO: Remove
        # ckan 2.9: Adding variables that were removed from c object for
        # compatibility with templates in existing extensions
        g.group_dict['package_count'] = query['count']

        extra_vars["search_facets"] = g.search_facets = query['search_facets']
        extra_vars["search_facets_limits"] = g.search_facets_limits = {}
        for facet in g.search_facets.keys():
            limit = int(
                request.params.get(u'_%s_limit' % facet,
                                   config.get(u'search.facets.default', 10)))
            g.search_facets_limits[facet] = limit
        extra_vars["page"].items = query['results']

        extra_vars["sort_by_selected"] = sort_by

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.facet_titles = facets
    g.page = extra_vars["page"]

    extra_vars["group_type"] = group_type
    _setup_template_variables(context, {u'id': id}, group_type=group_type)
    return extra_vars


def _update_facet_titles(facets, group_type):
    for plugin in plugins.PluginImplementations(plugins.IFacets):
        facets = plugin.group_facets(facets, group_type, None)
    return facets


def _get_group_dict(id, group_type):
    u''' returns the result of group_show action or aborts if there is a
    problem '''
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'for_view': True
    }
    try:
        return _action(u'group_show')(context, {
            u'id': id,
            u'include_datasets': False
        })
    except (NotFound, NotAuthorized):
        base.abort(404, _(u'Group not found'))


def read(group_type, is_organization, id=None, limit=20):
    extra_vars = {}
    set_org(is_organization)
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'schema': _db_to_form_schema(group_type=group_type),
        u'for_view': True
    }
    data_dict = {u'id': id, u'type': group_type}

    # unicode format (decoded from utf8)
    q = request.params.get(u'q', u'')

    extra_vars["q"] = q

    try:
        # Do not query for the group datasets when dictizing, as they will
        # be ignored and get requested on the controller anyway
        data_dict['include_datasets'] = False

        # Do not query group members as they aren't used in the view
        data_dict['include_users'] = False

        group_dict = _action(u'group_show')(context, data_dict)
        group = context['group']
    except (NotFound, NotAuthorized):
        base.abort(404, _(u'Group not found'))

    # if the user specified a group id, redirect to the group name
    if data_dict['id'] == group_dict['id'] and \
            data_dict['id'] != group_dict['name']:

        url_with_name = h.url_for(u'{}.read'.format(group_type),
                                  id=group_dict['name'])

        return h.redirect_to(
            h.add_url_param(alternative_url=url_with_name))

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.q = q
    g.group_dict = group_dict
    g.group = group

    extra_vars = _read(id, limit, group_type)

    extra_vars["group_type"] = group_type
    extra_vars["group_dict"] = group_dict

    return base.render(
        _get_group_template(u'read_template', g.group_dict['type']),
        extra_vars)


def activity(id, group_type, is_organization, offset=0):
    u'''Render this group's public activity stream page.'''
    extra_vars = {}
    set_org(is_organization)
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'for_view': True
    }
    try:
        group_dict = _get_group_dict(id, group_type)
    except (NotFound, NotAuthorized):
        base.abort(404, _(u'Group not found'))

    try:
        # Add the group's activity stream (already rendered to HTML) to the
        # template context for the group/read.html
        # template to retrieve later.
        extra_vars["activity_stream"] = \
            _action(u'organization_activity_list'
                    if group_dict.get(u'is_organization')
                    else u'group_activity_list')(
            context, {
                u'id': group_dict['id'],
                u'offset': offset
            })

    except ValidationError as error:
        base.abort(400, error.message)

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.group_activity_stream = extra_vars["activity_stream"]
    g.group_dict = group_dict

    extra_vars["group_type"] = group_type
    extra_vars["group_dict"] = group_dict
    extra_vars["id"] = id
    return base.render(
        _get_group_template(u'activity_template', group_type), extra_vars)


def about(id, group_type, is_organization):
    extra_vars = {}
    set_org(is_organization)
    context = {u'model': model, u'session': model.Session, u'user': g.user}
    group_dict = _get_group_dict(id, group_type)
    group_type = group_dict['type']
    _setup_template_variables(context, {u'id': id}, group_type=group_type)

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.group_dict = group_dict
    g.group_type = group_type

    extra_vars = {u"group_dict": group_dict,
                  u"group_type": group_type}

    return base.render(
        _get_group_template(u'about_template', group_type), extra_vars)


def members(id, group_type, is_organization):
    extra_vars = {}
    set_org(is_organization)
    context = {u'model': model, u'session': model.Session, u'user': g.user}

    try:
        data_dict = {u'id': id}
        check_access(u'group_edit_permissions', context, data_dict)
        members = get_action(u'member_list')(context, {
            u'id': id,
            u'object_type': u'user'
        })
        data_dict['include_datasets'] = False
        group_dict = _action(u'group_show')(context, data_dict)
    except NotFound:
        base.abort(404, _(u'Group not found'))
    except NotAuthorized:
        base.abort(403,
                   _(u'User %r not authorized to edit members of %s') %
                   (g.user, id))

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.members = members
    g.group_dict = group_dict

    extra_vars = {
        u"members": members,
        u"group_dict": group_dict,
        u"group_type": group_type
    }
    return base.render(_replace_group_org(u'group/members.html'), extra_vars)


def member_delete(id, group_type, is_organization):
    extra_vars = {}
    set_org(is_organization)
    if u'cancel' in request.params:
        return h.redirect_to(u'{}.members'.format(group_type), id=id)

    context = {u'model': model, u'session': model.Session, u'user': g.user}

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
            return h.redirect_to(u'{}.members'.format(group_type), id=id)
        user_dict = _action(u'group_show')(context, {u'id': user_id})

        # TODO: Remove
        # ckan 2.9: Adding variables that were removed from c object for
        # compatibility with templates in existing extensions
        g.user_dict = user_dict
        g.user_id = user_id
        g.group_id = id

    except NotAuthorized:
        base.abort(403, _(u'Unauthorized to delete group %s members') % u'')
    except NotFound:
        base.abort(404, _(u'Group not found'))
    extra_vars = {
        u"user_id": user_id,
        u"user_dict": user_dict,
        u"group_id": id
    }
    return base.render(_replace_group_org(u'group/confirm_delete_member.html'),
                       extra_vars)


# deprecated
def history(id, group_type, is_organization):
    return h.redirect_to(u'group.activity', id=id)


def follow(id, group_type, is_organization):
    u'''Start following this group.'''
    set_org(is_organization)
    context = {u'model': model, u'session': model.Session, u'user': g.user}
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
    context = {u'model': model, u'session': model.Session, u'user': g.user}
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
    extra_vars = {}
    set_org(is_organization)
    context = {u'model': model, u'session': model.Session, u'user': g.user}
    group_dict = _get_group_dict(id, group_type)
    try:
        followers = \
            get_action(u'group_follower_list')(context, {u'id': id})
    except NotAuthorized:
        base.abort(403, _(u'Unauthorized to view followers %s') % u'')

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.group_dict = group_dict
    g.followers = followers

    extra_vars = {
        u"group_dict": group_dict,
        u"group_type": group_type,
        u"followers": followers
    }
    return base.render(u'group/followers.html', extra_vars)


def admins(id, group_type, is_organization):
    extra_vars = {}
    set_org(is_organization)
    group_dict = _get_group_dict(id, group_type)
    admins = authz.get_group_or_org_admin_ids(id)

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.group_dict = group_dict
    g.admins = admins

    extra_vars = {
        u"group_dict": group_dict,
        u'group_type': group_type,
        u"admins": admins
    }

    return base.render(
        _get_group_template(u'admins_template', group_dict['type']),
        extra_vars)


class BulkProcessView(MethodView):
    u''' Bulk process view'''

    def _prepare(self, group_type, id=None):

        # check we are org admin

        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'schema': _db_to_form_schema(group_type=group_type),
            u'for_view': True,
            u'extras_as_string': True
        }
        return context

    def get(self, id, group_type, is_organization):
        extra_vars = {}
        set_org(is_organization)
        context = self._prepare(group_type, id)
        data_dict = {u'id': id, u'type': group_type}
        data_dict['include_datasets'] = False
        try:
            group_dict = _action(u'group_show')(context, data_dict)
            group = context['group']
        except NotFound:
            base.abort(404, _(u'Group not found'))

        if not group_dict['is_organization']:
            # FIXME: better error
            raise Exception(u'Must be an organization')

        # If no action then just show the datasets
        limit = 500
        # TODO: Remove
        # ckan 2.9: Adding variables that were removed from c object for
        # compatibility with templates in existing extensions
        g.group_dict = group_dict
        g.group = group
        extra_vars = _read(id, limit, group_type)
        g.packages = g.page.items

        extra_vars = {
            u"group_dict": group_dict,
            u"group": group,
            u"page": g.page,
            u"packages": g.page.items,
            u'group_type': group_type
        }

        return base.render(
            _get_group_template(u'bulk_process_template', group_type),
            extra_vars)

    def post(self, id, group_type, is_organization, data=None):
        set_org(is_organization)
        context = self._prepare(group_type)
        data_dict = {u'id': id, u'type': group_type}
        try:
            check_access(u'bulk_update_public', context, {u'org_id': id})
            # Do not query for the group datasets when dictizing, as they will
            # be ignored and get requested on the controller anyway
            data_dict['include_datasets'] = False
            group_dict = _action(u'group_show')(context, data_dict)
            group = context['group']
        except NotFound:
            group_label = h.humanize_entity_type(
                u'organization' if is_organization else u'group',
                group_type,
                u'default label') or _(
                    u'Organization' if is_organization else u'Group')
            base.abort(404, _(u'{} not found'.format(group_label)))
        except NotAuthorized:
            base.abort(403,
                       _(u'User %r not authorized to edit %s') % (g.user, id))

        if not group_dict['is_organization']:
            # FIXME: better error
            raise Exception(u'Must be an organization')

        # TODO: Remove
        # ckan 2.9: Adding variables that were removed from c object for
        # compatibility with templates in existing extensions
        g.group_dict = group_dict
        g.group = group

        # use different form names so that ie7 can be detected
        form_names = set([
            u"bulk_action.public",
            u"bulk_action.delete",
            u"bulk_action.private"
        ])
        actions_in_form = set(request.form.keys())
        actions = form_names.intersection(actions_in_form)
        # ie7 puts all buttons in form params but puts submitted one twice

        for key, value in six.iteritems(request.form.to_dict()):
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

        data_dict = {u'datasets': datasets, u'org_id': group_dict['id']}

        try:
            get_action(action_functions[action])(context, data_dict)
        except NotAuthorized:
            base.abort(403, _(u'Not authorized to perform bulk update'))
        return h.redirect_to(u'{}.bulk_process'.format(group_type), id=id)


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
            data_dict.update(clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.files)))
            ))
            data_dict['type'] = group_type or u'group'
            context['message'] = data_dict.get(u'log_message', u'')
            data_dict['users'] = [{u'name': g.user, u'capacity': u'admin'}]
            group = _action(u'group_create')(context, data_dict)

        except (NotFound, NotAuthorized) as e:
            base.abort(404, _(u'Group not found'))
        except dict_fns.DataError:
            base.abort(400, _(u'Integrity Error'))
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(group_type, is_organization,
                            data_dict, errors, error_summary)

        return h.redirect_to(group['type'] + u'.read', id=group['name'])

    def get(self, group_type, is_organization,
            data=None, errors=None, error_summary=None):
        extra_vars = {}
        set_org(is_organization)
        context = self._prepare()
        data = data or clean_dict(
            dict_fns.unflatten(
                tuplize_dict(
                    parse_params(request.args, ignore_keys=CACHE_PARAMETERS)
                )
            )
        )

        if not data.get(u'image_url', u'').startswith(u'http'):
            data.pop(u'image_url', None)
        errors = errors or {}
        error_summary = error_summary or {}
        extra_vars = {
            u'data': data,
            u'errors': errors,
            u'error_summary': error_summary,
            u'action': u'new',
            u'group_type': group_type
        }
        _setup_template_variables(
            context, data, group_type=group_type)
        form = base.render(
            _get_group_template(u'group_form', group_type), extra_vars)

        # TODO: Remove
        # ckan 2.9: Adding variables that were removed from c object for
        # compatibility with templates in existing extensions
        g.form = form

        extra_vars["form"] = form
        return base.render(
            _get_group_template(u'new_template', group_type), extra_vars)


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
            data_dict.update(clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.files)))
            ))
            context['message'] = data_dict.get(u'log_message', u'')
            data_dict['id'] = context['id']
            context['allow_partial_update'] = True
            group = _action(u'group_update')(context, data_dict)
            if id != group['name']:
                _force_reindex(group)

        except (NotFound, NotAuthorized) as e:
            base.abort(404, _(u'Group not found'))
        except dict_fns.DataError:
            base.abort(400, _(u'Integrity Error'))
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(id, group_type, is_organization,
                            data_dict, errors, error_summary)
        return h.redirect_to(group[u'type'] + u'.read', id=group[u'name'])

    def get(self, id, group_type, is_organization,
            data=None, errors=None, error_summary=None):
        extra_vars = {}
        set_org(is_organization)
        context = self._prepare(id, is_organization)
        data_dict = {u'id': id, u'include_datasets': False}
        try:
            group_dict = _action(u'group_show')(context, data_dict)
        except (NotFound, NotAuthorized):
            base.abort(404, _(u'Group not found'))
        data = data or group_dict
        errors = errors or {}
        extra_vars = {
            u'data': data,
            u"group_dict": group_dict,
            u'errors': errors,
            u'error_summary': error_summary,
            u'action': u'edit',
            u'group_type': group_type
        }

        _setup_template_variables(context, data, group_type=group_type)
        form = base.render(
            _get_group_template(u'group_form', group_type), extra_vars)

        # TODO: Remove
        # ckan 2.9: Adding variables that were removed from c object for
        # compatibility with templates in existing extensions
        g.grouptitle = group_dict.get(u'title')
        g.groupname = group_dict.get(u'name')
        g.data = data
        g.group_dict = group_dict

        extra_vars["form"] = form
        return base.render(
            _get_group_template(u'edit_template', group_type), extra_vars)


class DeleteGroupView(MethodView):
    u'''Delete group view '''

    def _prepare(self, id=None):
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
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
            group_label = h.humanize_entity_type(
                u'group',
                group_type,
                u'has been deleted') or _(u'Group')
            h.flash_notice(
                _(u'%s has been deleted.') % _(group_label))
            group_dict = _action(u'group_show')(context, {u'id': id})
        except NotAuthorized:
            base.abort(403, _(u'Unauthorized to delete group %s') % u'')
        except NotFound:
            base.abort(404, _(u'Group not found'))
        except ValidationError as e:
            h.flash_error(e.error_dict['message'])
            return h.redirect_to(u'organization.read', id=id)

            return h.redirect_to(u'{}.read'.format(group_type), id=id)
        # TODO: Remove
        g.group_dict = group_dict

        return h.redirect_to(u'{}.index'.format(group_type))

    def get(self, group_type, is_organization, id=None):
        extra_vars = {}
        set_org(is_organization)
        context = self._prepare(id)
        group_dict = _action(u'group_show')(context, {u'id': id})
        if u'cancel' in request.params:
            return h.redirect_to(u'{}.edit'.format(group_type), id=id)

        # TODO: Remove
        g.group_dict = group_dict
        extra_vars = {
            u"group_dict": group_dict,
            u"group_type": group_type
        }
        return base.render(_replace_group_org(u'group/confirm_delete.html'),
                           extra_vars)


class MembersGroupView(MethodView):
    u'''New members group view'''

    def _prepare(self, id=None):
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user
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
            group_dict = _action(u'group_member_create')(context, data_dict)
        except NotAuthorized:
            base.abort(403, _(u'Unauthorized to add member to group %s') % u'')
        except NotFound:
            base.abort(404, _(u'Group not found'))
        except ValidationError as e:
            h.flash_error(e.error_summary)
            return h.redirect_to(u'{}.member_new'.format(group_type), id=id)

        # TODO: Remove
        g.group_dict = group_dict

        return h.redirect_to(u'{}.members'.format(group_type), id=id)

    def get(self, group_type, is_organization, id=None):
        extra_vars = {}
        set_org(is_organization)
        context = self._prepare(id)
        user = request.params.get(u'user')
        data_dict = {u'id': id}
        data_dict['include_datasets'] = False
        group_dict = _action(u'group_show')(context, data_dict)
        roles = _action(u'member_roles_list')(context, {
            u'group_type': group_type
        })
        if user:
            user_dict = get_action(u'user_show')(context, {u'id': user})
            user_role =\
                authz.users_role_for_group_or_org(id, user) or u'member'
            # TODO: Remove
            g.user_dict = user_dict
            extra_vars["user_dict"] = user_dict
        else:
            user_role = u'member'

        # TODO: Remove
        g.group_dict = group_dict
        g.roles = roles
        g.user_role = user_role

        extra_vars.update({
            u"group_dict": group_dict,
            u"roles": roles,
            u"user_role": user_role,
            u"group_type": group_type
        })
        return base.render(_replace_group_org(u'group/member_new.html'),
                           extra_vars)


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
