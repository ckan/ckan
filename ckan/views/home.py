# encoding: utf-8

from flask import Blueprint, render_template, abort
from flask.views import View

import ckan.model as model
import ckan.logic as logic
import ckan.lib.search as search
from ckan.common import g, c, config, _
import ckan.lib.helpers as h

CACHE_PARAMETERS = ['__cache', '__no_cache__']

home = Blueprint(
    u'home', __name__, url_prefix=u'/')


@home.before_request
def before_request():
    try:
        print 'Before Request'
        context = {
            u'model': model,
            u'user': g.user,
            'auth_user_obj': g.userobj
        }
        # views.identify_user()
        logic.check_access(u'site_read', context)
    except logic.NotAuthorized:
        abort(403)


class HomeView(View):
    def dispatch_request(self):
        try:
            # package search
            context = {'model': model, 'session': model.Session,
                       'user': g.user, 'auth_user_obj': g.userobj}
            data_dict = {
                'q': '*:*',
                'facet.field': h.facets(),
                'rows': 4,
                'start': 0,
                'sort': 'views_recent desc',
                'fq': 'capacity:"public"'
            }
            query = logic.get_action('package_search')(
                context, data_dict)
            g.search_facets = query['search_facets']
            g.package_count = query['count']
            g.datasets = query['results']

            g.facet_titles = {
                'organization': _('Organizations'),
                'groups': _('Groups'),
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

        return render_template(u'home/index.html')


class AboutView(View):
    def dispatch_request(self):
        return render_template(u'home/about.html')


home.add_url_rule(u'/', view_func=HomeView.as_view('home'))
#home.add_url_rule(u'/home', view_func=HomeView.as_view('home'))
home.add_url_rule('about', view_func=AboutView.as_view('about'))
