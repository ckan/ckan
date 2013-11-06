import logging
import ckan.plugins as p

log = logging.getLogger(__name__)
ignore_empty = p.toolkit.get_validator('ignore_empty')


class WebPageView(p.SingletonPlugin):
    '''This extenstion makes views of webpage'''

    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourceView, inherit=True)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'theme/templates')

    def info(self):
        return {'name': 'webpage',
                'title': 'Web Page',
                'schema': {'page_url': [ignore_empty, unicode]},
                'iframed': False}

    def can_view(self, data_dict):
        return True

    def view_template(self, context, data_dict):
        return 'webpage_view.html'

    def form_template(self, context, data_dict):
        return 'webpage_form.html'
