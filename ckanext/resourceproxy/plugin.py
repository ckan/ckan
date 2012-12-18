from logging import getLogger

import ckan.lib.helpers as h
import ckan.plugins as p

log = getLogger(__name__)


def get_proxified_resource_url(data_dict):
    '''
    :param data_dict: contains a resource and package dict
    :type data_dict: dictionary
    '''
    url = h.url_for(
        action='proxy_resource',
        controller='ckanext.resourceproxy.controller:ProxyController',
        id=data_dict['package']['name'],
        resource_id=data_dict['resource']['id'])
    log.info('Proxified url is {0}'.format(url))
    return url


class ResourceProxy(p.SingletonPlugin):
    """A proxy for CKAN resources to get around the same
    origin policy for previews

    This extension implements the IRoute interface
      - ``IRoutes`` allows to add a route to the proxy action


    Instructions on how to use the extension:

    1. Import the proxy plugin if it exists
        ``import ckanext.resourceproxy.plugin as proxy``

    2. In you extension, make sure that the proxy plugin is
        enabled by checking the ``ckan.resource_proxy_enabled`` config variable.
        ``config.get('ckan.resource_proxy_enabled', False)``
    """
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IConfigurer, inherit=True)

    def update_config(self, config):
        config['ckan.resource_proxy_enabled'] = True

    def before_map(self, m):
        m.connect('/dataset/{id}/resource/{resource_id}/proxy',
                    controller='ckanext.resourceproxy.controller:ProxyController',
                    action='proxy_resource')
        return m
