# encoding: utf-8

from flask import Blueprint, abort, redirect

import ckan.model as model
import ckan.logic as logic
import ckan.lib.base as base
import ckan.lib.search as search
import ckan.lib.helpers as h

from ckan.common import g, config, _

CACHE_PARAMETERS = [u'__cache', u'__no_cache__']


home = Blueprint(u'home', __name__)


@home.before_request
def before_request():
    u'''set context and check authorization'''
    try:
        context = {
            u'model': model,
            u'user': g.user,
            u'auth_user_obj': g.userobj}
        logic.check_access(u'site_read', context)
    except logic.NotAuthorized:
        abort(403)


def index():
    u'''display home page'''
    try:
        context = {u'model': model, u'session': model.Session,
                   u'user': g.user, u'auth_user_obj': g.userobj}
        data_dict = {u'q': u'*:*',
                     u'facet.field': h.facets(),
                     u'rows': 4,
                     u'start': 0,
                     u'sort': u'view_recent desc',
                     u'fq': u'capacity:"public"'}
        query = logic.get_action(u'package_search')(context, data_dict)
        g.search_facets = query['search_facets']
        g.package_count = query['count']
        g.datasets = query['results']

        g.facet_titles = {
            u'organization': _(u'Organizations'),
            u'groups': _(u'Groups'),
            u'tags': _(u'Tags'),
            u'res_format': _(u'Formats'),
            u'license': _(u'Licenses'),
        }

    except search.SearchError:
        g.package_count = 0

    if g.userobj and not g.userobj.email:
        url = h.url_for(controller=u'user', action=u'edit')
        msg = _(u'Please <a href="%s">update your profile</a>'
                u' and add your email address. ') % url + \
            _(u'%s uses your email address'
                u' if you need to reset your password.') \
            % config.get(u'ckan.site_title')
        h.flash_notice(msg, allow_html=True)
    return base.render(u'home/index.html', extra_vars={})


def about():
    u''' display about page'''
    return base.render(u'home/about.html', extra_vars={})


def redirect_locale(target_locale, path=None):
    if path:
        target = u'/{}/{}'.format(target_locale, path)
    else:
        target = u'/{}'.format(target_locale)
    return redirect(target, code=308)


util_rules = [
    (u'/', index),
    (u'/about', about)
]
for rule, view_func in util_rules:
    home.add_url_rule(rule, view_func=view_func)

locales_mapping = [
    (u'zh_TW', u'zh_Hant_TW'),
    (u'zh_CN', u'zh_Hans_CN'),
]

for locale in locales_mapping:

    legacy_locale = locale[0]
    new_locale = locale[1]

    home.add_url_rule(
        u'/{}/'.format(legacy_locale),
        view_func=redirect_locale,
        defaults={u'target_locale': new_locale}
    )

    home.add_url_rule(
        u'/{}/<path:path>'.format(legacy_locale),
        view_func=redirect_locale,
        defaults={u'target_locale': new_locale}
    )
