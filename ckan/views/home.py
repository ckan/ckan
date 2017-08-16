# encoding: utf-8

from flask import Blueprint, render_template, abort
from flask.views import View

import ckan.model as model
import ckan.logic as logic
from ckan.common import g, request

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
        return render_template(u'home/index.html')


class AboutView(View):
    def dispatch_request(self):
        return render_template(u'home/about.html')


# home.add_url_rule(u'/', view_func=HomeView.as_view('home'))
# home.add_url_rule(u'/home', view_func=HomeView.as_view('home'))
home.add_url_rule('about', view_func=AboutView.as_view('about'))
