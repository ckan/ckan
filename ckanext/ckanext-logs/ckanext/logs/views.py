from typing import Any

from flask import Blueprint

import ckan.lib.base as base
from ckan import logic
from ckan.common import _, config, request
from ckan.lib.helpers import Page
from ckan.lib.helpers import helper_functions as h

logs = Blueprint(u'logs', __name__, url_prefix=u'/ckan-admin')

def index():
    page_number = h.get_page_number(request.args)
    default_limit: int = config.get('ckan.logs.limit', 10)
    limit = int(request.args.get('limit', default_limit))
    
    q = request.args.get('q', '')
    start_time = request.args.get('start_time', '')
    end_time = request.args.get('end_time', '')

    try:
        logic.check_access(u'show_logs', {})
    except logic.NotAuthorized:
        return base.abort(403, _(u'Need to be system administrator to administer'))
    
    logs = logic.get_action(u' ')(data_dict={
        u'q': q,
        u'limit': limit,
        u'page': page_number,
        u'start_time': start_time,
        u'end_time': end_time
    })
    
    extra_vars: dict[str, Any] = {}
    
    error_message = logs.get('error', None)
    if error_message:
        extra_vars[u'error'] = error_message
    else:
        extra_vars[u'page'] = Page(
            collection=logs.get('data'),
            page=page_number,
            url=h.pager_url,
            item_count=logs.get('total'),
            items_per_page=limit)
        extra_vars[u'page'].items = logs.get('data')
        extra_vars[u'q'] = logs.get('q')
        extra_vars[u'start_time'] = logs.get('start_time')
        extra_vars[u'end_time'] = logs.get('end_time')
        
    return base.render('admin/logs.html', extra_vars=extra_vars)

logs.add_url_rule(u'/logs', view_func=index, methods=(u'GET',))


def get_blueprints():
    return [logs]
