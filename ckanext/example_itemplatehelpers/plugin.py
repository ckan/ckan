import ckan.plugins as plugins


class ExampleITemplateHelpersPlugin(plugins.SingletonPlugin):
    '''An example that shows how to use the ITemplateHelpers plugin interface.

    '''
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)

    # Update CKAN's config settings, see the IConfigurer plugin interface.
    def update_config(self, config):

        # Tell CKAN to use the template files in
        # ckanext/example_itemplatehelpers/templates.
        plugins.toolkit.add_template_directory(config, 'templates')

    # Our custom template helper method.
    def example_helper(self):
        '''An example template helper method.'''

        # Just return some example text.
        return 'This is some example text.'

    # Tell CKAN what custom template helper methods this plugin provides,
    # see the ITemplateHelpers plugin interface.
    def get_helpers(self):
        return {'example_helper': self.example_helper}
