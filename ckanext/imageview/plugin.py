import logging
import ckan.plugins as p

log = logging.getLogger(__name__)
ignore_empty = p.toolkit.get_validator('ignore_empty')

DEFAULT_IMAGE_FORMATS = ['png', 'jpeg', 'jpg', 'gif']


class ImageView(p.SingletonPlugin):
    '''This plugin makes views of image resources, using an <img> tag'''

    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourceView, inherit=True)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'theme/templates')

    def info(self):
        return {'name': 'image_view',
                'title': p.toolkit._('Image'),
                'icon': 'picture',
                'schema': {'image_url': [ignore_empty, unicode]},
                'iframed': False,
                'always_available': True,
                'default_title': p.toolkit._('Image'),
                }

    def can_view(self, data_dict):
        return (data_dict['resource'].get('format', '').lower()
                in DEFAULT_IMAGE_FORMATS)

    def view_template(self, context, data_dict):
        return 'image_view.html'

    def form_template(self, context, data_dict):
        return 'image_form.html'
