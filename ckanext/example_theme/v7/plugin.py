import random

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


def dataset_of_the_day():
    '''Return the dataset of the day.

    '''
    # Get a list of the names of all of the site's datasets.
    dataset_names = toolkit.get_action('package_list')(data_dict={})

    # Choose one dataset name at random.
    dataset_name = random.choice(dataset_names)

    # Get the full dictionary object for the chosen dataset.
    dataset = toolkit.get_action('package_show')(
        data_dict={'id': dataset_name})

    return dataset


class ExampleThemePlugin(plugins.SingletonPlugin):
    '''An example theme plugin.

    '''
    plugins.implements(plugins.IConfigurer)

    # Declare that this plugin will implement ITemplateHelpers.
    plugins.implements(plugins.ITemplateHelpers)

    def update_config(self, config):

        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        toolkit.add_template_directory(config, 'templates')

    def get_helpers(self):
        '''Register the dataset_of_the_day() function above as a template
        helper function.

        '''
        # Template helper function names should begin with the name of the
        # extension they belong to, to avoid clashing with functions from
        # other extensions.
        return {'example_theme_dataset_of_the_day': dataset_of_the_day}
