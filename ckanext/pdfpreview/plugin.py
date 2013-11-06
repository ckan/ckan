import logging

import ckan.plugins as p
import ckan.lib.datapreview as datapreview

log = logging.getLogger(__name__)

try:
    import ckanext.resourceproxy.plugin as proxy
except ImportError:
    pass


class PdfPreview(p.SingletonPlugin):
    '''This extension previews PDFs. '''
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IResourceView, inherit=True)

    PDF = ['pdf', 'x-pdf', 'acrobat', 'vnd.pdf']
    proxy_is_enabled = False

    def info(self):
        return {'name': 'pdf', 'title': 'Pdf'}

    def update_config(self, config):
        p.toolkit.add_public_directory(config, 'theme/public')
        p.toolkit.add_template_directory(config, 'theme/templates')
        p.toolkit.add_resource('theme/public', 'ckanext-pdfpreview')

    def configure(self, config):
        enabled = config.get('ckan.resource_proxy_enabled', False)
        self.proxy_is_enabled = enabled

    def can_view(self, data_dict):
        resource = data_dict['resource']
        format_lower = resource['format'].lower()

        proxy_enabled = p.plugin_loaded('resource_proxy')
        same_domain = datapreview.on_same_domain(data_dict)

        if format_lower in self.PDF:
            if same_domain or proxy_enabled:
                return True
        return False

    def view_template(self, context, data_dict):
        return 'pdf.html'
