# encoding: utf-8

from logging import getLogger

import ckan.lib.helpers as h
import ckan.plugins as p
import ckan.lib.datapreview as datapreview
import urlparse
from ckan.common import config

log = getLogger(__name__)


def get_proxified_resource_url(data_dict, proxy_schemes=['http','https']):
    '''
    :param data_dict: contains a resource and package dict
    :type data_dict: dictionary
    :param proxy_schemes: list of url schemes to proxy for.
    :type data_dict: list
    '''

    ckan_url = config.get('ckan.site_url', '//localhost:5000')
    url = data_dict['resource']['url']
    scheme = urlparse.urlparse(url).scheme
    compare_domains = datapreview.compare_domains
    if not compare_domains([ckan_url, url]) and scheme in proxy_schemes:
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
    p.implements(p.ITemplateHelpers, inherit=True)


    def before_map(self, m):
        m.connect('/dataset/{id}/resource/{resource_id}/proxy',
                    controller='ckanext.resourceproxy.controller:ProxyController',
                    action='proxy_resource')
        return m

    def get_helpers(self):
        return {'view_resource_url': self.view_resource_url}

    def view_resource_url(self, resource_view, resource,
                          package, proxy_schemes=['http','https']):
        '''
        Returns the proxy url if its availiable
        '''
        data_dict = {'resource_view': resource_view,
                     'resource': resource,
                     'package': package}
        return get_proxified_resource_url(data_dict,
                                          proxy_schemes=proxy_schemes)
