# encoding: utf-8


import ckan.plugins as p
from ckan.config.declaration import Declaration, Key

ignore_empty = p.toolkit.get_validator('ignore_empty')
unicode_safe = p.toolkit.get_validator('unicode_safe')


class AudioView(p.SingletonPlugin):
    '''This plugin makes views of audio resources, using an <audio> tag'''

    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourceView, inherit=True)
    p.implements(p.IConfigDeclaration)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'theme/templates')
        self.formats = config.safe('ckan.preview.audio_formats').split()

    def info(self):
        return {'name': 'audio_view',
                'title': p.toolkit._('Audio'),
                'icon': 'file-audio-o',
                'schema': {'audio_url': [ignore_empty, unicode_safe]},
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

    # IConfigDeclaration

    def declare_config_options(self, declaration: Declaration, key: Key):
        declaration.annotate("audio_view settings")
        declaration.declare(key.ckan.preview.audio_formats, "wav ogg mp3")
