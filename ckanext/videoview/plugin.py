# encoding: utf-8

from six import text_type
import ckan.plugins as p

ignore_empty = p.toolkit.get_validator('ignore_empty')

DEFAULT_VIDEO_FORMATS = 'mp4 ogg webm'


class VideoView(p.SingletonPlugin):
    '''This plugin makes views of video resources, using a <video> tag'''

    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourceView, inherit=True)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'theme/templates')
        self.formats = config.get(
            'ckan.preview.video_formats',
            DEFAULT_VIDEO_FORMATS).split()

    def info(self):
        return {'name': 'video_view',
                'title': p.toolkit._('Video'),
                'icon': 'file-video-o',
                'schema': {'video_url': [ignore_empty, text_type],
                           'poster_url': [ignore_empty, text_type]},
                'iframed': False,
                'always_available': True,
                'default_title': p.toolkit._('Video'),
                }

    def can_view(self, data_dict):
        return (data_dict['resource'].get('format', '').lower()
                in self.formats)

    def view_template(self, context, data_dict):
        return 'video_view.html'

    def form_template(self, context, data_dict):
        return 'video_form.html'
