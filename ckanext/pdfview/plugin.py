# encoding: utf-8

import logging
from six import text_type
import ckan.plugins as p

log = logging.getLogger(__name__)
ignore_empty = p.toolkit.get_validator(u'ignore_empty')


class PDFView(p.SingletonPlugin):
    u'''This plugin makes views of PDF resources, using an <object> tag'''

    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourceView, inherit=True)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, u'theme/templates')

    def info(self):
        return {u'name': u'pdf_view',
                u'title': p.toolkit._(u'PDF'),
                u'icon': u'file-pdf-o',
                u'schema': {u'pdf_url': [ignore_empty, text_type]},
                u'iframed': False,
                u'always_available': False,
                u'default_title': p.toolkit._(u'PDF'),
                }

    def can_view(self, data_dict):
        return (data_dict['resource'].get(u'format', '').lower() == u'pdf')

    def view_template(self, context, data_dict):
        return u'pdf_view.html'

    def form_template(self, context, data_dict):
        return u'pdf_form.html'
