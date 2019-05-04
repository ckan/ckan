# encoding: utf-8

import logging
from six import text_type
import ckan.plugins as p

log = logging.getLogger(__name__)
ignore_empty = p.toolkit.get_validator('ignore_empty')

DEFAULT_IMAGE_FORMATS = 'png jpeg jpg gif'


class ImageView(p.SingletonPlugin):
    '''This plugin makes views of image resources, using an <img> tag'''

    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourceView, inherit=True)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'theme/templates')
        self.formats = config.get(
            'ckan.preview.image_formats',
            DEFAULT_IMAGE_FORMATS).split()

    def info(self):
        return {'name': 'image_view',
                'title': p.toolkit._('Image'),
                'icon': 'picture-o',
                'schema': {'image_url': [ignore_empty, text_type]},
                'iframed': False,
                'always_available': True,
                'default_title': p.toolkit._('Image'),
                }

    def can_view(self, data_dict):
        return (data_dict['resource'].get('format', '').lower()
                in self.formats)

    def view_template(self, context, data_dict):
        return 'image_view.html'

    def form_template(self, context, data_dict):
        return 'image_form.html'
