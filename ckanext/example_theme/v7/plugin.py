import random

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


def example_theme_dataset_of_the_day():
    '''Return the dataset of the day.

    '''
    dataset_names = toolkit.get_action('package_list')(data_dict={})
    dataset_name = random.choice(dataset_names)
    dataset = toolkit.get_action('package_show')(
        data_dict={'id': dataset_name})
    return dataset


class ExampleThemePlugin(plugins.SingletonPlugin):
    '''An example theme plugin.

    '''
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)

    def update_config(self, config):

        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        toolkit.add_template_directory(config, 'templates')

    def get_helpers(self):

        return {'example_theme_dataset_of_the_day':
                example_theme_dataset_of_the_day}
