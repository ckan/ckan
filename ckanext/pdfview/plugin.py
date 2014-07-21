import logging

import ckan.plugins as p
import ckan.lib.datapreview as datapreview

log = logging.getLogger(__name__)


class PdfView(p.SingletonPlugin):
    '''This extension views PDFs. '''
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IResourceView, inherit=True)
    p.implements(p.IPackageController, inherit=True)

    PDF = ['pdf', 'x-pdf', 'acrobat', 'vnd.pdf']
    proxy_is_enabled = False

    def info(self):
        return {'name': 'pdf', 'title': 'Pdf', 'icon': 'file-text'}

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

    def add_default_views(self, context, data_dict):
        resources = datapreview.get_new_resources(context, data_dict)
        for resource in resources:
            if self.can_view({'package': data_dict, 'resource': resource}):
                view = {'title': 'PDF View',
                        'description': 'PDF view of the resource.',
                        'resource_id': resource['id'],
                        'view_type': 'pdf'}
                p.toolkit.get_action('resource_view_create')(
                    {'defer_commit': True}, view
                )

    def after_update(self, context, data_dict):
        self.add_default_views(context, data_dict)

    def after_create(self, context, data_dict):
        self.add_default_views(context, data_dict)
