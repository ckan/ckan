import logging
import ckan.plugins as p
import ckan.lib.datapreview as datapreview

log = logging.getLogger(__name__)
ignore_empty = p.toolkit.get_validator('ignore_empty')


class WebPageView(p.SingletonPlugin):
    '''This extension makes views of webpage'''

    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourceView, inherit=True)
    p.implements(p.IPackageController, inherit=True)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'theme/templates')

    def info(self):
        return {'name': 'webpage',
                'title': 'Web Page',
                'schema': {'page_url': [ignore_empty, unicode]},
                'iframed': False,
                'icon': 'link'}

    def can_view(self, data_dict):
        return True

    def view_template(self, context, data_dict):
        return 'webpage_view.html'

    def form_template(self, context, data_dict):
        return 'webpage_form.html'

    def add_default_views(self, context, data_dict):
        resources = datapreview.get_new_resources(context, data_dict)
        for resource in resources:
            if (resource.get('format', '').lower() in ['html', 'htm'] or
                    resource['url'].split('.')[-1] in ['html', 'htm']):
                view = {'title': 'Web Page View',
                        'description': 'View of the webpage',
                        'resource_id': resource['id'],
                        'view_type': 'webpage'}
                p.toolkit.get_action('resource_view_create')(
                    {'defer_commit': True, 'ignore_auth': True}, view
                )

    def after_update(self, context, data_dict):
        self.add_default_views(context, data_dict)

    def after_create(self, context, data_dict):
        self.add_default_views(context, data_dict)
