from logging import getLogger

import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
import ckan.lib.base as base

import ckanext.resourceproxy.plugin as proxy

log = getLogger(__name__)


class JsonPreview(p.SingletonPlugin):
    """This extension previews JSON(P)

    This extension implements two interfaces

      - ``IConfigurer`` allows to modify the configuration
      - ``IResourcePreview`` allows to add previews
    """
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourcePreview, inherit=True)

    def __init__(self):
        self.proxy_enabled = True

    def update_config(self, config):
        ''' Set up the resource library, public directory and
        template directory for the preview
        '''
        toolkit.add_public_directory(config, 'theme/public')
        toolkit.add_template_directory(config, 'theme/templates')
        toolkit.add_resource('theme/public', 'ckanext-jsonpreview')

    def can_preview(self, resource):
        format_lower = resource['format'].lower()
        return format_lower in ['jsonp'] or format_lower in ['json'] and self.proxy_enabled

    def setup_template_variables(self, context, data_dict):
        base.c.resource['url'] = proxy.get_proxyfied_resource_url(data_dict)

    def preview_template(self, context):
        return 'json.html'
