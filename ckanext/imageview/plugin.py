import logging
import ckan.plugins as p
import ckan.lib.datapreview as datapreview

log = logging.getLogger(__name__)
ignore_empty = p.toolkit.get_validator('ignore_empty')

DEFAULT_IMAGE_FORMATS = ['png', 'jpeg', 'jpg', 'gif']


class ImageView(p.SingletonPlugin):
    '''This extension makes views of images'''

    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourceView, inherit=True)
    p.implements(p.IPackageController, inherit=True)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'theme/templates')

    def info(self):
        return {'name': 'image',
                'title': 'Image',
                'icon': 'picture',
                'schema': {'image_url': [ignore_empty, unicode]},
                'iframed': False}

    def can_view(self, data_dict):
        return True

    def view_template(self, context, data_dict):
        return 'image_view.html'

    def form_template(self, context, data_dict):
        return 'image_form.html'

    def add_default_views(self, context, data_dict):
        resources = p.toolkit.get_new_resources(context, data_dict)
        for resource in resources:
            if resource.get('format', '').lower() in DEFAULT_IMAGE_FORMATS:
                view = {'title': 'Resource Image',
                        'description': 'View of the Image',
                        'resource_id': resource['id'],
                        'view_type': 'image'}
                p.toolkit.get_action('resource_view_create')(
                    {'defer_commit': True}, view
                )

    def after_update(self, context, data_dict):
        self.add_default_views(context, data_dict)

    def after_create(self, context, data_dict):
        self.add_default_views(context, data_dict)
