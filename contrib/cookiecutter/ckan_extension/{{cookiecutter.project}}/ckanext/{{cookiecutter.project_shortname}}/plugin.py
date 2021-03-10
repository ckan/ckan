import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


class {{ cookiecutter.plugin_class_name }}(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('assets',
            '{{ cookiecutter.project_shortname }}')
