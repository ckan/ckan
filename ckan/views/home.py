# encoding: utf-8

from flask import Blueprint, abort, redirect

import ckan.model as model
import ckan.logic as logic
import ckan.lib.base as base
import ckan.lib.search as search
import ckan.lib.helpers as h

from ckan.common import g, config, _

CACHE_PARAMETERS = ['__cache', '__no_cache__']


home = Blueprint('home', __name__)


@home.before_request
def before_request():
    '''set context and check authorization'''
    try:
        context = {
            'model': model,
            'user': g.user,
            'auth_user_obj': g.userobj}
        logic.check_access('site_read', context)
    except logic.NotAuthorized:
        abort(403)


def index():
    '''display home page'''
    try:
        context = {'model': model, 'session': model.Session,
                   'user': g.user, 'auth_user_obj': g.userobj}
        data_dict = {'q': '*:*',
                     'facet.field': h.facets(),
                     'rows': 4,
                     'start': 0,
                     'sort': 'view_recent desc',
                     'fq': 'capacity:"public"'}
        query = logic.get_action('package_search')(context, data_dict)
        g.search_facets = query['search_facets']
        g.package_count = query['count']
        g.datasets = query['results']

        org_label = h.humanize_entity_type(
            'organization',
            h.default_group_type('organization'),
            'facet label') or _('Organizations')

        group_label = h.humanize_entity_type(
            'group',
            h.default_group_type('group'),
            'facet label') or _('Groups')

        g.facet_titles = {
            'organization': org_label,
            'groups': group_label,
            'tags': _('Tags'),
            'res_format': _('Formats'),
            'license': _('Licenses'),
        }

    except search.SearchError:
        g.package_count = 0

    if g.userobj and not g.userobj.email:
        url = h.url_for(controller='user', action='edit')
        msg = _('Please <a href="%s">update your profile</a>'
                ' and add your email address. ') % url + \
            _('%s uses your email address'
                ' if you need to reset your password.') \
            % config.get('ckan.site_title')
        h.flash_notice(msg, allow_html=True)
    return base.render('home/index.html', extra_vars={})


def about():
    ''' display about page'''
    return base.render('home/about.html', extra_vars={})


def redirect_locale(target_locale, path=None):
    target = f'/{target_locale}/{path}' if path else f'/{target_locale}'
    return redirect(target, code=308)


util_rules = [
    ('/', index),
    ('/about', about)
]
for rule, view_func in util_rules:
    home.add_url_rule(rule, view_func=view_func)

locales_mapping = [
    ('zh_TW', 'zh_Hant_TW'),
    ('zh_CN', 'zh_Hans_CN'),
]

for locale in locales_mapping:

    legacy_locale = locale[0]
    new_locale = locale[1]

    home.add_url_rule(
        f'/{legacy_locale}/',
        view_func=redirect_locale,
        defaults={'target_locale': new_locale}
    )

    home.add_url_rule(
        f'/{legacy_locale}/<path:path>',
        view_func=redirect_locale,
        defaults={'target_locale': new_locale}
    )
