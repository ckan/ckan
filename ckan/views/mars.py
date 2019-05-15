# encoding: utf-8

import logging
from flask import Blueprint, abort

import ckan.model as model
import ckan.logic as logic
import ckan.lib.base as base
import ckan.lib.search as search
import ckan.lib.helpers as h

from ckan.common import g, config, _, request

mars = Blueprint(u'mars', __name__)

log = logging.getLogger(__name__)


@mars.before_request
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
    u'''display mars page'''
    try:
        context = {u'model': model, u'session': model.Session,
                   u'user': g.user, u'auth_user_obj': g.userobj}
        data_dict = {u'q': u'*:*',
                     u'facet.field': h.facets(),
                     u'rows': 4,
                     u'start': 4,
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
    return base.render(u'mars/index.html', extra_vars={})


def reqaccess(data=None, errors=None, error_summary=None):
    u''' display access request form page'''

    log.info('MaRS view, fn reqaccess, req params: %s' % request.params)

    from_email = g.userobj.email if g.userobj and g.userobj.email else u'your_email@domain.com'
    maintainer_email = request.params.get('maintainer_email', u'')

    errors = errors or {}
    error_summary = error_summary or {}

    data = data or {
        'subject': u'AVIN Data Request',
        'to': maintainer_email,
        'from': from_email,
        'title': u'Title',
        }

    extra_vars = {
        u'data': data,
        u'errors': errors,
        u'error_summary': error_summary,
    }

    return base.render(u'mars/access_form.html', extra_vars)


util_rules = [
    (u'/', index),
    (u'/reqaccess', reqaccess)
]
for rule, view_func in util_rules:
    mars.add_url_rule(rule, view_func=view_func)
