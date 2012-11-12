import urllib2
from logging import getLogger

import ckan.logic as logic
import ckan.lib.base as base

log = getLogger(__name__)


@logic.side_effect_free
def proxy_resource(context, data_dict):
        resource_id = data_dict['resource_id']
        log.info('Proxify resource {id}'.format(id=resource_id))
        resource = logic.get_action('resource_show')(context, {'id': resource_id})
        url = resource['url']
        try:
            req = urllib2.urlopen(url)
        except urllib2.HTTPError, error:
            req = error
        base.response.headers = req.headers

        import shutil
        shutil.copyfileobj(req, base.response)


class ProxyController(base.BaseController):
    def proxy_resource(self, resource_id):
        data_dict = {'resource_id': resource_id}
        context = {'model': base.model, 'session': base.model.Session,
                   'user': base.c.user or base.c.author}
        return proxy_resource(context, data_dict)
