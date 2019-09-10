# encoding: utf-8

from logging import getLogger

import requests
from six.moves.urllib.parse import urlsplit
from flask import Blueprint, make_response

import ckan.lib.base as base
import ckan.logic as logic
from ckan.common import config, _
from ckan.plugins.toolkit import (asint, abort, get_action, c)

log = getLogger(__name__)

MAX_FILE_SIZE = asint(
    config.get(u'ckan.resource_proxy.max_file_size', 1024**2)
)
CHUNK_SIZE = asint(config.get(u'ckan.resource_proxy.chunk_size', 4096))

resource_proxy = Blueprint(u'resource_proxy', __name__)


def proxy_resource(context, data_dict):
    u'''Chunked proxy for resources. To make sure that the file is not too
    large, first, we try to get the content length from the headers.
    If the headers to not contain a content length (if it is a chinked
    response), we only transfer as long as the transferred data is
    less than the maximum file size.

    '''
    resource_id = data_dict[u'resource_id']
    log.info(u'Proxify resource {id}'.format(id=resource_id))
    try:
        resource = get_action(u'resource_show')(context, {u'id': resource_id})
    except logic.NotFound:
        return abort(404, _(u'Resource not found'))
    url = resource[u'url']

    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return abort(409, _(u'Invalid URL.'))

    response = make_response()
    try:
        # first we try a HEAD request which may not be supported
        did_get = False
        r = requests.head(url)
        # Servers can refuse HEAD requests. 405 is the appropriate
        # response, but 400 with the invalid method mentioned in the
        # text, or a 403 (forbidden) status is also possible (#2412,
        # #2530)
        if r.status_code in (400, 403, 405):
            r = requests.get(url, stream=True)
            did_get = True
        r.raise_for_status()

        cl = r.headers.get(u'content-length')
        if cl and int(cl) > MAX_FILE_SIZE:
            return abort(
                409, (
                    u'Content is too large to be proxied. Allowed'
                    u'file size: {allowed}, Content-Length: {actual}.'
                ).format(allowed=MAX_FILE_SIZE, actual=cl)
            )

        if not did_get:
            r = requests.get(url, stream=True)

        response.headers[u'content-type'] = r.headers[u'content-type']
        response.charset = r.encoding

        length = 0
        for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
            response.stream.write(chunk)
            length += len(chunk)

            if length >= MAX_FILE_SIZE:
                return abort(
                    409,
                    headers={u'content-encoding': u''},
                    detail=u'Content is too large to be proxied.'
                )

    except requests.exceptions.HTTPError as error:
        details = u'Could not proxy resource. Server responded with %s %s' % (
            error.response.status_code, error.response.reason
        )
        return abort(409, detail=details)
    except requests.exceptions.ConnectionError as error:
        details = u'''Could not proxy resource because a
                            connection error occurred. %s''' % error
        return abort(502, detail=details)
    except requests.exceptions.Timeout:
        details = u'Could not proxy resource because the connection timed out.'
        return abort(504, detail=details)
    return response


def proxy_view(id, resource_id):
    data_dict = {u'resource_id': resource_id}
    context = {
        u'model': base.model,
        u'session': base.model.Session,
        u'user': c.user
    }
    return proxy_resource(context, data_dict)


resource_proxy.add_url_rule(
    u'/dataset/<id>/resource/<resource_id>/proxy', view_func=proxy_view
)
