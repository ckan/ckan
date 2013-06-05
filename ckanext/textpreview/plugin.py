from logging import getLogger

import ckan.plugins as p

from ckan.common import json

log = getLogger(__name__)

proxy = False
try:
    import ckanext.resourceproxy.plugin as proxy
except ImportError:
    pass


DEFAULT_TEXT_FORMATS = ['text/plain', 'txt', 'plain']
DEFAULT_XML_FORMATS = ['xml', 'rdf', 'rdf+xm', 'owl+xml', 'atom', 'rss']
DEFAULT_JSON_FORMATS = ['json', 'gjson', 'geojson']
DEFAULT_JSONP_FORMATS = ['jsonp']


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

    proxy_is_enabled = False

    def update_config(self, config):
        ''' Set up the resource library, public directory and
        template directory for the preview
        '''

        self.text_formats = config.get(
            'ckan.preview.text_formats', '').split()
        if not self.text_formats:
            self.text_formats = DEFAULT_TEXT_FORMATS

        self.xml_formats = config.get(
            'ckan.preview.xml_formats', '').split()
        if not self.xml_formats:
            self.xml_formats = DEFAULT_XML_FORMATS

        self.json_formats = config.get(
            'ckan.preview.json_formats', '').split()
        if not self.json_formats:
            self.json_formats = DEFAULT_JSON_FORMATS

        self.jsonp_formats = config.get(
            'ckan.preview.jsonp_formats', '').split()
        if not self.jsonp_formats:
            self.jsonp_formats = DEFAULT_JSONP_FORMATS

        self.no_jsonp_formats = (self.text_formats +
                                 self.xml_formats +
                                 self.json_formats)

        p.toolkit.add_public_directory(config, 'theme/public')
        p.toolkit.add_template_directory(config, 'theme/templates')
        p.toolkit.add_resource('theme/public', 'ckanext-textpreview')

    def configure(self, config):
        self.proxy_is_enabled = config.get(
            'ckan.resource_proxy_enabled', False)

    def can_preview(self, data_dict):
        resource = data_dict['resource']
        format_lower = resource['format'].lower()
        if format_lower in self.jsonp_formats:
            return True
        elif format_lower in self.no_jsonp_formats and (
                self.proxy_is_enabled or resource['on_same_domain']):
            return True
        return False

    def setup_template_variables(self, context, data_dict):
        assert self.can_preview(data_dict)
        p.toolkit.c.preview_metadata = json.dumps({
            'text_formats': self.text_formats,
            'json_formats': self.json_formats,
            'jsonp_formats': self.jsonp_formats,
            'xml_formats': self.xml_formats
        })
        resource = data_dict['resource']
        format_lower = resource['format'].lower()
        if (format_lower in self.no_jsonp_formats and
                self.proxy_is_enabled and not resource['on_same_domain']):
            p.toolkit.c.resource['url'] = proxy.get_proxified_resource_url(
                data_dict)

    def preview_template(self, context, data_dict):
        return 'text.html'
