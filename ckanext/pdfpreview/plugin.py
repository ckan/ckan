from logging import getLogger

import ckan.plugins as p
import ckan.plugins.toolkit as toolkit

log = getLogger(__name__)


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

    def requires_same_orign(self, resource):
        #TODO: return True
        return False

    def can_preview(self, resource):
        format_lower = resource['format'].lower()
        return format_lower in self.PDF

    def preview_template(self, context):
        return 'dataviewer/pdf.html'
