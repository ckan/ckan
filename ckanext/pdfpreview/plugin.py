from logging import getLogger

import ckan.plugins as p
import ckan.lib.base as base

log = getLogger(__name__)

proxy = False
try:
    import ckanext.resourceproxy.plugin as proxy
except ImportError:
    pass


class PdfPreview(p.SingletonPlugin):
    """This extension previews PDFs

    This extension implements two interfaces

      - ``IConfigurer`` allows to modify the configuration
      - ``IConfigurable`` get the configuration
      - ``IResourcePreview`` allows to add previews
    """
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IResourcePreview, inherit=True)

    PDF = ['pdf', 'x-pdf', 'acrobat', 'vnd.pdf']
    proxy_is_enabled = False

    def update_config(self, config):
        ''' Set up the resource library, public directory and
        template directory for the preview
        '''
        p.toolkit.add_public_directory(config, 'theme/public')
        p.toolkit.add_template_directory(config, 'theme/templates')
        p.toolkit.add_resource('theme/public', 'ckanext-pdfpreview')

    def configure(self, config):
        self.proxy_is_enabled = config.get('ckan.resource_proxy_enabled', False)

    def can_preview(self, data_dict):
        resource = data_dict['resource']
        format_lower = resource['format'].lower()
        return format_lower in self.PDF and (resource['on_same_domain'] or self.proxy_is_enabled)

    def setup_template_variables(self, context, data_dict):
        if self.proxy_is_enabled and not data_dict['resource']['on_same_domain']:
            base.c.resource['url'] = proxy.get_proxified_resource_url(data_dict)

    def preview_template(self, context, data_dict):
        return 'pdf.html'
