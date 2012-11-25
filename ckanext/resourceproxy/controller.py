import urllib2
import shutil
from logging import getLogger

import ckan.logic as logic
import ckan.lib.base as base

log = getLogger(__name__)


def proxy_resource(context, data_dict):
        resource_id = data_dict['resource_id']
        log.info('Proxify resource {id}'.format(id=resource_id))
        resource = logic.get_action('resource_show')(context, {'id': resource_id})
        url = resource['url']
        had_http_error = False
        try:
            res = urllib2.urlopen(url)
        except urllib2.HTTPError, error:
            res = error
            had_http_error = True
        except urllib2.URLError, error:
            details = "Could not proxy resource. %s" % str(error.reason)
            base.abort(500, detail=details)
        base.response.headers = res.headers

        shutil.copyfileobj(res, base.response)

        # todo only change the status code, not the whole content
        if had_http_error and hasattr(res, 'code'):
            base.abort(res.code)


class ProxyController(base.BaseController):
    def proxy_resource(self, resource_id):
        data_dict = {'resource_id': resource_id}
        context = {'model': base.model, 'session': base.model.Session,
                   'user': base.c.user or base.c.author}
        return proxy_resource(context, data_dict)
