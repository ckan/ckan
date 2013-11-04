import logging

import ckan.plugins as p
from ckan.lib.navl.validators import ignore_empty

log = logging.getLogger(__name__)

DEFAULT_IMAGE_FORMATS = ['png', 'jpeg', 'jpg', 'gif']


class ImageView(p.SingletonPlugin):
    '''This extenstion makes views of images'''

    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourceView, inherit=True)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'theme/templates')

    def info(self):
        return {'name': 'image',
                'title': 'Image',
                'schema': {'image_url': [ignore_empty, unicode]}}

    def can_view(self, data_dict):
        return True

    def view_template(self, context, data_dict):
        return 'image_view.html'

    def form_template(self, context, data_dict):
        return 'image_form.html'
