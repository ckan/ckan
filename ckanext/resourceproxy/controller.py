from logging import getLogger

import requests

import ckan.logic as logic
import ckan.lib.base as base

log = getLogger(__name__)

MAX_FILE_SIZE = 1024 * 1024 * 2  # 2MB
CHUNK_SIZE = 256


def proxy_resource(context, data_dict):
        resource_id = data_dict['resource_id']
        log.info('Proxify resource {id}'.format(id=resource_id))
        resource = logic.get_action('resource_show')(context, {'id': resource_id})
        url = resource['url']

        try:
            r = requests.get(url)
            r.raise_for_status()

            # write body
            cl = r.headers['content-length']
            if cl and int(cl) > MAX_FILE_SIZE:
                base.abort(500, '''Content is too large to be proxied.
                    Allowed file size: {allowed}.
                    Content-Length: {actual}'''.format(
                        allowed=MAX_FILE_SIZE, actual=cl))

            # write headers
            base.response.headers = r.headers

            # we have to pretend that the response is not gzipped or deflated
            # because we don't want request to unzip the content.
            r.headers['content-encoding'] = ''

            length = 0
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE, decode_unicode=False):
                base.response.body_file.write(chunk)
                length += len(chunk)

                if length >= MAX_FILE_SIZE:
                    base.abort(500, headers={'content-encoding': ''},
                        detail='Content is too large to be proxied.')

        except requests.exceptions.HTTPError, error:
            details = 'Could not proxy resource. %s' % str(error.response.reason)
            base.abort(error.response.status_code, detail=details)
        except requests.exceptions.ConnectionError, error:
            details = '''Could not proxy resource because a
                                connection error occurred. %s''' % str(error)
            base.abort(500, detail=details)
        except requests.exceptions.Timeout, error:
            details = 'Could not proxy resource because the connection timed out.'
            base.abort(500, detail=details)


class ProxyController(base.BaseController):
    def proxy_resource(self, resource_id):
        data_dict = {'resource_id': resource_id}
        context = {'model': base.model, 'session': base.model.Session,
                   'user': base.c.user or base.c.author}
        return proxy_resource(context, data_dict)
