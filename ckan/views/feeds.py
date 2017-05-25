import os
import cgi
import logging

from flask import Blueprint, make_response
from werkzeug.exceptions import BadRequest

from ckan.common import _, config, g, request, response, json
import ckan.lib.helpers as h
import ckan.model as model
import ckan.logic as logic


log = logging.getLogger(__name__)

feeds = Blueprint(u'feeds', __name__, url_prefix=u'/feeds')

ITEMS_LIMIT = 20


def _package_search(data_dict):
    """
    Helper method that wraps the package_search action.

     * unless overridden, sorts results by metadata_modified date
     * unless overridden, sets a default item limit
    """
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': g.userobj}
    if 'sort' not in data_dict or not data_dict['sort']:
        data_dict['sort'] = u'metadata_modified desc'

    if 'rows' not in data_dict or not data_dict['rows']:
        data_dict['rows'] = ITEMS_LIMIT

    # package_search action modifies the data_dict, so keep our copy intact.
    query = logic.get_action('package_search')(context, data_dict.copy())

    return query['count'], query['results']

@feeds.route('/custom.atom')
def custom():
    '''Custom atom feed'''
    print 'Helo'
    q = request.params.get('q', u'')
    fq = ''
    search_params = {}
    for (param, value) in request.params.items():
        if param not in ['q', 'page', 'sort'] \
                and len(value) and not param.startswith('_'):
            search_params[param] = value
            fq += '%s:"%s"' % (param, value)

    page = h.get_page_number(request.params)

    limit = ITEMS_LIMIT
    data_dict = {
        'q': q,
        'fq': fq,
        'start': (page - 1) * limit,
        'rows': limit,
        'sort': request.params.get('sort', None)
    }

    item_count, results = _package_search(data_dict)


# Routing
# feeds.add_url_rule(u'/custom.atom', methods=[u'GET', u'POST'], custom)
