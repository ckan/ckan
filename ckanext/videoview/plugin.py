# encoding: utf-8

import logging
from six import text_type
import ckan.plugins as p

log = logging.getLogger(__name__)
ignore_empty = p.toolkit.get_validator(u'ignore_empty')

DEFAULT_VIDEO_FORMATS = u'video/mp4'


class VideoView(p.SingletonPlugin):
    u'''This plugin makes views of video resources, using an <video> tag'''

    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourceView, inherit=True)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, u'theme/templates')
        self.formats = config.get(
            u'ckan.preview.video_formats',
            DEFAULT_VIDEO_FORMATS).split()

    def info(self):
        return {u'name': u'video_view',
                u'title': p.toolkit._(u'Video'),
                u'icon': u'file-video-o',
                u'schema': {u'video_url': [ignore_empty, text_type]},
                u'iframed': False,
                u'always_available': True,
                u'default_title': p.toolkit._(u'Video'),
                }

    def can_view(self, data_dict):
        return (data_dict[u'resource'].get(u'format', u'').lower()
                in self.formats)

    def view_template(self, context, data_dict):
        return u'video_view.html'

    def form_template(self, context, data_dict):
        return u'video_form.html'
