# encoding: utf-8

from flask import Blueprint, render_template, abort
from flask.views import View

import ckan.model as model
import ckan.logic as logic
import ckan.lib.search as search
from ckan.common import g, c, config, _
import ckan.lib.helpers as h

CACHE_PARAMETERS = [u'__cache', u'__no_cache__']

home = Blueprint(u'home', __name__)


@home.before_request
def before_request():
    try:
        context = {
            u'model': model,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        # views.identify_user()
        logic.check_access(u'site_read', context)
    except logic.NotAuthorized:
        abort(403)


class HomeView(View):
    def dispatch_request(self):
        try:
            # package search
            context = {u'model': model, u'session': model.Session,
                       u'user': g.user, u'auth_user_obj': g.userobj}
            data_dict = {
                u'q': u'*:*',
                u'facet.field': h.facets(),
                u'rows': 4,
                u'start': 0,
                u'sort': u'views_recent desc',
                u'fq': u'capacity:"public"'
            }
            query = logic.get_action(u'package_search')(
                context, data_dict)
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

        return render_template(u'home/index.html')


class AboutView(View):
    def dispatch_request(self):
        return render_template(u'home/about.html')


util_rules = [
    (u'/', HomeView.as_view("index")),
    (u'/home', HomeView.as_view("home")),
    (u'/about', AboutView.as_view("about"))]

for rule, view_func in util_rules:
    home.add_url_rule(rule, view_func=view_func)
