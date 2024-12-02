# encoding: utf-8

from flask import Blueprint
import json

from typing import cast
from ckan.types import Context

import ckan.lib.base as base
from ckan.lib.helpers import helper_functions as h
from ckan.common import _, request
from ckan.types import Response
from ckan.plugins import toolkit
from ckan import model
from ckan.views.api import _finish_ok, _finish


util = Blueprint(u'util', __name__)


def internal_redirect() -> Response:
    u''' Redirect to the url parameter.
    Only internal URLs are allowed'''

    url = request.form.get(u'url') or request.args.get(u'url')
    if not url:
        base.abort(400, _(u'Missing Value') + u': url')

    url = url.replace('\r', ' ').replace('\n', ' ').replace('\0', ' ')
    if h.url_is_local(url):
        return h.redirect_to(url)
    else:
        base.abort(403, _(u'Redirecting to external site is not allowed.'))


def primer() -> str:
    u''' Render all HTML components out onto a single page.
    This is useful for development/styling of CKAN. '''

    return base.render(u'development/primer.html')


def search_rebuild_progress(entity_id: str):
    context = cast(Context, {
        'model': model,
        'session': model.Session,
        'user': toolkit.g.user,
    })

    try:
        task_status = toolkit.get_action('task_status_show')(
                            context, {'entity_id': entity_id,
                                      'task_type': 'reindex_packages',
                                      'key': 'search_rebuild'})
    except toolkit.NotAuthorized:
        return _finish(403, _('Not authorized to view task status'), 'json')
    except toolkit.ObjectNotFound:
        return _finish(404, _('Task not found'), 'json')

    task_status['value'] = json.loads(task_status.get('value', '{}'))
    task_status['error'] = json.loads(task_status.get('error', '{}'))

    messages = {
        'pending': _('In queue to re-index records'),
        'running': _('Currently re-indexing records'),
        'complete': _('All records indexed'),
        'unknown': _('Unknown'),
    }

    return_dict = {
        'total': task_status.get('value', {}).get('total', 0),
        'current': task_status.get('value', {}).get('indexed', 0),
        'label': messages.get(task_status.get('state', 'unknown')),
        'last_updated': h.render_datetime(
            task_status.get('last_updated'), '%Y-%m-%d %H:%M:%S %Z') if
            task_status.get('last_updated') else None,
    }

    return _finish_ok(return_dict)


util.add_url_rule(
    u'/util/redirect', view_func=internal_redirect, methods=(u'GET', u'POST',))
util.add_url_rule(u'/testing/primer', view_func=primer)
util.add_url_rule('/util/search_rebuild_progress/<entity_id>',
                  view_func=search_rebuild_progress, methods=['GET'])
