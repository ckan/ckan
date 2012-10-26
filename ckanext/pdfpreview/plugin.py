from logging import getLogger

import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
import ckan.lib.base as base

log = getLogger(__name__)

proxy = False
try:
    import ckanext.resourceproxy.plugin as proxy
except:
    pass


class PdfPreview(p.SingletonPlugin):
    """This extension previews PDFs

    This extension implements two interfaces

      - ``IConfigurer`` allows to modify the configuration
      - ``IResourcePreview`` allows to add previews
    """
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourcePreview, inherit=True)

    PDF = ['pdf', 'x-pdf', 'acrobat', 'vnd.pdf']

    def update_config(self, config):
        ''' Set up the resource library, public directory and
        template directory for the preview
        '''
        toolkit.add_public_directory(config, 'theme/public')
        toolkit.add_template_directory(config, 'theme/templates')
        toolkit.add_resource('theme/public', 'ckanext-pdfpreview')

    def can_preview(self, data_dict):
        resource = data_dict['resource']
        format_lower = resource['format'].lower()
        return format_lower in self.PDF and (resource['on_same_domain'] or proxy)

    def setup_template_variables(self, context, data_dict):
        if proxy and not data_dict['resource']['on_same_domain']:
            base.c.resource['url'] = proxy.get_proxyfied_resource_url(data_dict)

    def preview_template(self, context):
        return 'pdf.html'
