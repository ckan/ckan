# encoding: utf-8

import logging
import datetime
from urllib import urlencode

from pylons.i18n import get_lang

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.lib.search as search
import ckan.model as model
import ckan.authz as authz
import ckan.lib.plugins
import ckan.plugins as plugins
from ckan.common import OrderedDict, c, g, config, request, _
from flask import Blueprint
import ckan.lib.plugins as lib_plugins

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params

log = logging.getLogger(__name__)

group = Blueprint('group', __name__, url_prefix=u'/group')
organization = Blueprint('organization', __name__, url_prefix=u'/organization')

lookup_group_plugin = ckan.lib.plugins.lookup_group_plugin
lookup_group_controller = ckan.lib.plugins.lookup_group_controller

group_types = ['group']


def _index_template(group_type):
    return lookup_group_plugin(group_type).index_template()


def _group_form(group_type=None):
    return lookup_group_plugin(group_type).group_form()


def _replace_group_org(string):
    ''' substitute organization for group if this is an org'''
    return string


def _setup_template_variables(context, data_dict, group_type=None):
        return lookup_group_plugin(group_type).\
            setup_template_variables(context, data_dict)


def _new_template(group_type):
    return lookup_group_plugin(group_type).new_template()


def _action(action_name):
    ''' select the correct group/org action '''
    return get_action(_replace_group_org(action_name))


def _save_new(context, group_type=None):
    try:
        data_dict = clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(request.params))))
        data_dict['type'] = group_type or 'group'
        context['message'] = data_dict.get('log_message', '')
        data_dict['users'] = [{'name': g.user, 'capacity': 'admin'}]

        h.redirect_to(group['type'] + '_read', id=group['name'])
    except (NotFound, NotAuthorized), e:
        base.abort(404, _('Group not found'))
    except dict_fns.DataError:
        base.abort(400, _(u'Integrity Error'))
    except ValidationError, e:
        errors = e.error_dict
        error_summary = e.error_summary
        return new(data_dict, errors, error_summary)


@group.before_request
def before_request():
    try:
        context = dict(model=model, user=g.user, auth_user_obj=g.userobj)
        check_access(u'site_read', context)
    except NotAuthorized:
        _, action = request.url_rule.endpoint.split(u'.')
        if action not in (u'group_list', ):
            base.abort(403, _(u'Not authorized to see this page'))


def index():
    group_type = 'group'
    page = h.get_page_number(request.params) or 1
    items_per_page = 21

    context = {
        'model': model,
        'session': model.Session,
        'user': c.user,
        'for_view': True,
        'with_private': False
    }

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


def new(data=None, errors=None, error_summary=None):
    if data and 'type' in data:
        group_type = data['type']
    else:
        group_type = 'group'
    if data:
        data['type'] = group_type

    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'save': 'save' in request.params,
        'parent': request.params.get('parent', None)
    }

    try:
        check_access('group_create', context)
    except NotAuthorized:
        base.abort(403, _('Unauthorized to create a group'))

    if context['save'] and not data:
        return _save_new(context, group_type)

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
        'group_type': group_type
    }
    _setup_template_variables(context, data, group_type=group_type)
    c.form = base.render(_group_form(group_type=group_type), extra_vars=vars)
    return base.render(
        _new_template(group_type), extra_vars={'group_type': group_type})


# Routing
group.add_url_rule(u'/', view_func=index, strict_slashes=False)
group.add_url_rule(u'/new', view_func=new)
