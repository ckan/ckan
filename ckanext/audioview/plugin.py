# encoding: utf-8

from six import text_type
import ckan.plugins as p

ignore_empty = p.toolkit.get_validator('ignore_empty')

DEFAULT_AUDIO_FORMATS = 'wav ogg mp3'


class AudioView(p.SingletonPlugin):
    '''This plugin makes views of audio resources, using an <audio> tag'''

    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourceView, inherit=True)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'theme/templates')
        self.formats = config.get(
            'ckan.preview.audio_formats',
            DEFAULT_AUDIO_FORMATS).split()

    def info(self):
        return {'name': 'audio_view',
                'title': p.toolkit._('Audio'),
                'icon': 'file-audio-o',
                'schema': {'audio_url': [ignore_empty, text_type]},
                'iframed': False,
                'always_available': True,
                'default_title': p.toolkit._('Audio'),
                }

    def can_view(self, data_dict):
        return (data_dict['resource'].get('format', '').lower()
                in self.formats)

    def view_template(self, context, data_dict):
        return 'audio_view.html'

    def form_template(self, context, data_dict):
        return 'audio_form.html'
