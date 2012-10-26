from logging import getLogger

import ckan.plugins as p
import ckan.lib.base as base

import controller

log = getLogger(__name__)


def get_proxyfied_resource_url(data_dict):
    url = base.h.url_for(
        action='proxy_resource',
        id=data_dict['package']['name'],
        resource_id=data_dict['resource']['id'])
    log.info('Proxified url is {0}'.format(url))
    return url


class ResourceProxy(p.SingletonPlugin):
    """A proxy for CKAN resources to get around the same
    origin policy for previews

    This extension implements two interfaces

      - ``IConfigurer`` allows to modify the configuration
      - ``IRoutes`` allows to add a route to the proxy action
      - ``IActions`` allows to add an action for the proxy
    """
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IActions)

    def before_map(self, m):
        m.connect('/dataset/{id}/resource/{resource_id}/proxy',
                    controller='ckanext.resourceproxy.controller:ProxyController',
                    action='proxy_resource')
        return m

    def get_actions(self):
        return {'proxy_resource': controller.proxy_resource}
