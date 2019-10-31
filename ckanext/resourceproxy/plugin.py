# encoding: utf-8

from logging import getLogger

from six.moves.urllib.parse import urlparse

import ckan.lib.helpers as h
import ckan.plugins as p
import ckan.lib.datapreview as datapreview
from ckan.common import config

from ckanext.resourceproxy import blueprint

log = getLogger(__name__)


def get_proxified_resource_url(data_dict, proxy_schemes=[u'http', u'https']):
    u'''
    :param data_dict: contains a resource and package dict
    :type data_dict: dictionary
    :param proxy_schemes: list of url schemes to proxy for.
    :type data_dict: list
    '''
    url = data_dict[u'resource'][u'url']
    if not p.plugin_loaded(u'resource_proxy'):
        return url

    ckan_url = config.get(u'ckan.site_url', u'//localhost:5000')
    scheme = urlparse(url).scheme
    compare_domains = datapreview.compare_domains
    if not compare_domains([ckan_url, url]) and scheme in proxy_schemes:
        url = h.url_for(
            u'resource_proxy.proxy_view',
            id=data_dict[u'package'][u'name'],
            resource_id=data_dict[u'resource'][u'id']
        )
        log.info(u'Proxified url is {0}'.format(url))
    return url


class ResourceProxy(p.SingletonPlugin):
    """A proxy for CKAN resources to get around the same
    origin policy for previews

    This extension implements the IRoute interface
      - ``IRoutes`` allows to add a route to the proxy action


    Instructions on how to use the extension:

    1. Import the proxy plugin if it exists
        ``import ckanext.resourceproxy.plugin as proxy``

    2. In you extension, make sure that the proxy plugin is enabled by
        checking the ``ckan.resource_proxy_enabled`` config variable.
        ``config.get('ckan.resource_proxy_enabled', False)``

    """
    p.implements(p.ITemplateHelpers, inherit=True)
    p.implements(p.IBlueprint)

    def get_blueprint(self):
        return blueprint.resource_proxy

    def get_helpers(self):
        return {u'view_resource_url': self.view_resource_url}

    def view_resource_url(
        self,
        resource_view,
        resource,
        package,
        proxy_schemes=[u'http', u'https']
    ):
        u'''
        Returns the proxy url if its availiable
        '''
        data_dict = {
            u'resource_view': resource_view,
            u'resource': resource,
            u'package': package
        }
        return get_proxified_resource_url(
            data_dict, proxy_schemes=proxy_schemes
        )
