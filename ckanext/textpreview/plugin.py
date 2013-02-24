from logging import getLogger

import ckan.plugins as p

log = getLogger(__name__)

proxy = False
try:
    import ckanext.resourceproxy.plugin as proxy
except ImportError:
    pass


class TextPreview(p.SingletonPlugin):
    """This extension previews JSON(P)

    This extension implements two interfaces

      - ``IConfigurer`` allows to modify the configuration
      - ``IConfigurable`` get the configuration
      - ``IResourcePreview`` allows to add previews
    """
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IResourcePreview, inherit=True)

    # don't forget to change public/preview.js as well if you edit the formats here
    TEXT_FORMATS = ['text/plain', 'txt', 'plain']
    XML_FORMATS = ['xml', 'rdf', 'rdf+xm', 'owl+xml', 'atom', 'rss']
    JSON_FORMATS = ['json']
    JSONP_FORMATS = ['jsonp']
    NO_JSONP_FORMATS = TEXT_FORMATS + XML_FORMATS + JSON_FORMATS

    proxy_is_enabled = False

    def update_config(self, config):
        ''' Set up the resource library, public directory and
        template directory for the preview
        '''
        p.toolkit.add_public_directory(config, 'theme/public')
        p.toolkit.add_template_directory(config, 'theme/templates')
        p.toolkit.add_resource('theme/public', 'ckanext-textpreview')

    def configure(self, config):
        self.proxy_is_enabled = config.get('ckan.resource_proxy_enabled', False)

    def can_preview(self, data_dict):
        resource = data_dict['resource']
        format_lower = resource['format'].lower()
        if format_lower in self.JSONP_FORMATS:
            return True
        elif format_lower in self.NO_JSONP_FORMATS and (self.proxy_is_enabled or resource['on_same_domain']):
            return True
        return False

    def setup_template_variables(self, context, data_dict):
        assert self.can_preview(data_dict)
        resource = data_dict['resource']
        format_lower = resource['format'].lower()
        if format_lower in self.NO_JSONP_FORMATS and self.proxy_is_enabled and not resource['on_same_domain']:
            p.toolkit.c.resource['url'] = proxy.get_proxified_resource_url(data_dict)

    def preview_template(self, context, data_dict):
        return 'text.html'
