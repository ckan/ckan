# encoding: utf-8
from __future__ import annotations

from ckan.types import Context
from typing import Any
from ckan.common import CKANConfig
import logging

import ckan.plugins as p
from ckan.config.declaration import Declaration, Key

log = logging.getLogger(__name__)
ignore_empty = p.toolkit.get_validator('ignore_empty')
unicode_safe = p.toolkit.get_validator('unicode_safe')


class ImageView(p.SingletonPlugin):
    '''This plugin makes views of image resources, using an <img> tag'''

    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourceView, inherit=True)
    p.implements(p.IConfigDeclaration)

    def update_config(self, config: CKANConfig):
        p.toolkit.add_template_directory(config, 'theme/templates')
        self.formats = config.get_value('ckan.preview.image_formats').split()

    def info(self) -> dict[str, Any]:
        return {'name': 'image_view',
                'title': p.toolkit._('Image'),
                'icon': 'picture-o',
                'schema': {'image_url': [ignore_empty, unicode_safe]},
                'iframed': False,
                'always_available': True,
                'default_title': p.toolkit._('Image'),
                }

    def can_view(self, data_dict: dict[str, Any]):
        return (data_dict['resource'].get('format', '').lower()
                in self.formats)

    def view_template(self, context: Context, data_dict: dict[str, Any]):
        return 'image_view.html'

    def form_template(self, context: Context, data_dict: dict[str, Any]):
        return 'image_form.html'

    # IConfigDeclaration

    def declare_config_options(self, declaration: Declaration, key: Key):
        section = key.ckan.preview

        declaration.annotate("image_view settings")
        declaration.declare(
            section.image_formats, "png jpeg jpg gif"
        ).set_description(
            "Customize which image formats the image_view plugin will show"
        )
