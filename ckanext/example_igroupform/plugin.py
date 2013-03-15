import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.plugins as lib_plugins
import ckan.lib.navl.validators as validators
import ckan.logic.schema
import ckan.logic.converters as converters

class ExampleIGroupFormPlugin(plugins.SingletonPlugin,
        lib_plugins.DefaultGroupForm):
    '''An example CKAN plugin that adds some custom metadata fields to groups.

    '''
    plugins.implements(plugins.IConfigurer, inherit=True)
    plugins.implements(plugins.IGroupForm, inherit=True)

    def update_config(self, config):
        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        toolkit.add_template_directory(config, 'templates')

    def is_fallback(self):
        # Register this plugin as the default IGroupForm plugin that is used
        # when no IGroupForm matches the type of the group being edited.
        return True

    def group_types(self):
        # This plugin doesn't handle any special group types (it just acts
        # as the default plugin for group's with type None).
        return []

    def form_to_db_schema(self):
        schema = ckan.logic.schema.group_form_schema()

        # Add our custom country_code metadata field to the schema.
        schema.update({
            'country_code': [validators.ignore_missing,
                converters.convert_to_extras]
            })

        # Add our custom website_url metadata field to the schema.
        schema.update({'website_url': [validators.ignore_missing,
            converters.convert_to_extras]})

        return schema

    def db_to_form_schema(self):
        schema = ckan.logic.schema.group_form_schema()

        # Add our custom country_code metadata field to the schema.
        schema.update({
            'country_code': [
                converters.convert_from_extras, validators.ignore_missing]
            })

        # Add our custom website_url metadata field to the schema.
        schema.update({'website_url': [converters.convert_from_extras,
            validators.ignore_missing]})

        return schema

    def check_data_dict(self, data_dict):
        # If the user submits a website URL that doesn't start with http://,
        # prepend it for them.
        website_url = data_dict.get('website_url', None)
        if website_url:
            if not website_url.startswith('http://'):
                website_url = 'http://' + website_url
                data_dict['website_url'] = website_url

    def setup_template_variables(self, context, data_dict=None):
        lib_plugins.DefaultGroupForm.setup_template_variables(self, context,
                data_dict)

        # Add this list of available country codes to the template context.
        toolkit.c.country_codes = ('de', 'en', 'fr', 'nl')
