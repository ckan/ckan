# encoding: utf-8

"""Home blueprint - replaces ckan.controllers.home"""

from flask import Blueprint, render_template, request, g, make_response
import ckan.logic as logic
import ckan.lib.helpers as h
import ckan.model as model

home = Blueprint('home', __name__)


@home.route('/')
def index():
    """Home page"""
    try:
        context = {'model': model, 'session': model.Session,
                   'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}
        data_dict = {
            'q': '*:*',
            'facet.field': ['groups', 'tags', 'res_format', 'license_id'],
            'rows': 4,
            'start': 0,
            'sort': 'metadata_modified desc',
            'fq': 'capacity:"public"'
        }
        query = logic.get_action('package_search')(context, data_dict)

        # Get group data
        group_data = logic.get_action('group_list')(
            context, {'all_fields': True, 'include_extras': True}
        )

        return render_template('home/index.html',
                             package_count=query['count'],
                             facets=query.get('facets', {}),
                             search_facets=query.get('search_facets', {}),
                             groups=group_data)

    except Exception as e:
        return render_template('home/index.html',
                             package_count=0,
                             facets={},
                             search_facets={},
                             groups=[])


@home.route('/about')
def about():
    """About page"""
    return render_template('home/about.html')


@home.route('/__invite__/')
def cors_options():
    """Handle CORS OPTIONS requests"""
    response = make_response('', 200)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CKAN-API-Key'
    return response
