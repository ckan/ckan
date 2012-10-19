from logging import getLogger

import ckan.plugins as p
import ckan.plugins.toolkit as toolkit

log = getLogger(__name__)


class JsonPreview(p.SingletonPlugin):
    """This extension previews JSON(P)

    This extension implements two interfaces

      - ``IConfigurer`` allows to modify the configuration
      - ``IResourcePreview`` allows to add previews
    """
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourcePreview, inherit=True)

    def update_config(self, config):
        ''' Set up the resource library, public directory and
        template directory for the preview
        '''
        toolkit.add_public_directory(config, 'theme/public')
        toolkit.add_template_directory(config, 'theme/templates')
        toolkit.add_resource('theme/public', 'ckanext-jsonpreview')

    def requires_same_orign(self, resource):
        ''' json resources have to be from the same origin. jsonp resources don't
        '''
        format_lower = resource['format'].lower()
        return format_lower in ['json']

    def can_preview(self, resource):
        format_lower = resource['format'].lower()
        return format_lower in ['jsonp', 'json']

    def preview_template(self, context):
        return 'json.html'
