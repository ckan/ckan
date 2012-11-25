import pylons
from logging import getLogger

import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
import ckan.lib.base as base

log = getLogger(__name__)

proxy = False
try:
    import ckanext.resourceproxy.plugin as proxy
except ImportError:
    pass


class JsonPreview(p.SingletonPlugin):
    """This extension previews JSON(P)

    This extension implements two interfaces

      - ``IConfigurer`` allows to modify the configuration
      - ``IResourcePreview`` allows to add previews
    """
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourcePreview, inherit=True)

    JSON_FORMATS = ['json']
    JSONP_FORMATS = ['jsonp']

    def update_config(self, config):
        ''' Set up the resource library, public directory and
        template directory for the preview
        '''
        toolkit.add_public_directory(config, 'theme/public')
        toolkit.add_template_directory(config, 'theme/templates')
        toolkit.add_resource('theme/public', 'ckanext-jsonpreview')

    def proxy_enabled(self):
        return pylons.config.get('ckan.resource_proxy_enabled', False)

    def can_preview(self, data_dict):
        resource = data_dict['resource']
        format_lower = resource['format'].lower()
        if format_lower in self.JSONP_FORMATS:
            return True
        elif format_lower in self.JSON_FORMATS and (self.proxy_enabled() or resource['on_same_domain']):
            return True
        return False

    def setup_template_variables(self, context, data_dict):
        assert self.can_preview(data_dict)
        resource = data_dict['resource']
        format_lower = resource['format'].lower()
        if format_lower in self.JSON_FORMATS and self.proxy_enabled() and not resource['on_same_domain']:
            base.c.resource['url'] = proxy.get_proxified_resource_url(data_dict)

    def preview_template(self, context, data_dict):
        return 'json.html'
