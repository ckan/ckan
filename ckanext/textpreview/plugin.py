import logging

from ckan.common import json
import ckan.plugins as p
import ckanext.resourceproxy.plugin as proxy

log = logging.getLogger(__name__)

DEFAULT_TEXT_FORMATS = ['text/plain', 'txt', 'plain']
DEFAULT_XML_FORMATS = ['xml', 'rdf', 'rdf+xm', 'owl+xml', 'atom', 'rss']
DEFAULT_JSON_FORMATS = ['json', 'gjson', 'geojson']
DEFAULT_JSONP_FORMATS = ['jsonp']


class TextPreview(p.SingletonPlugin):
    '''This extension previews JSON(P).'''

    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IResourceView, inherit=True)

    proxy_is_enabled = False

    def update_config(self, config):
        text_formats = config.get('ckan.preview.text_formats', '').split()
        self.text_formats = text_formats or DEFAULT_TEXT_FORMATS

        xml_formats = config.get('ckan.preview.xml_formats', '').split()
        self.xml_formats = xml_formats or DEFAULT_XML_FORMATS

        json_formats = config.get('ckan.preview.json_formats', '').split()
        self.json_formats = json_formats or DEFAULT_JSON_FORMATS

        jsonp_formats = config.get('ckan.preview.jsonp_formats', '').split()
        self.jsonp_formats = jsonp_formats or DEFAULT_JSONP_FORMATS

        self.no_jsonp_formats = (self.text_formats +
                                 self.xml_formats +
                                 self.json_formats)

        p.toolkit.add_public_directory(config, 'theme/public')
        p.toolkit.add_template_directory(config, 'theme/templates')
        p.toolkit.add_resource('theme/public', 'ckanext-textpreview')

    def configure(self, config):
        self.proxy_is_enabled = config.get('ckan.resource_proxy_enabled')

    def info(self):
        return {'name': 'text', 'title': 'Text'}

    def can_view(self, data_dict):
        resource = data_dict['resource']
        format_lower = resource['format'].lower()

        if format_lower in self.jsonp_formats:
            return True
        elif format_lower in self.no_jsonp_formats:
            return True
            # if self.proxy_is_enabled or resource['on_same_domain']:
            #     return {'can_preview': True, 'quality': quality}
            # else:
            #     return {'can_preview': False,
            #             'fixable': 'Enable resource_proxy',
            #             'quality': quality}
        return False

    def setup_template_variables(self, context, data_dict):
        metadata = {'text_formats': self.text_formats,
                    'json_formats': self.json_formats,
                    'jsonp_formats': self.jsonp_formats,
                    'xml_formats': self.xml_formats}
        return {'preview_metadata': json.dumps(metadata),
                'resource_json': json.dumps(data_dict['resource'])}
        # resource = data_dict['resource']
        # format_lower = resource['format'].lower()
        # if (format_lower in self.no_jsonp_formats and
        #         self.proxy_is_enabled and not resource['on_same_domain']):
        #     url = proxy.get_proxified_resource_url(data_dict)
        #     p.toolkit.c.resource['url'] = url

    def view_template(self, context, data_dict):
        return 'text_view.html'

    def form_template(self, context, data_dict):
        return 'text_form.html'
