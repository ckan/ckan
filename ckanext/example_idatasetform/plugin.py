import logging
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.plugins as lib_plugins
import ckan.lib.navl.validators as validators
import ckan.logic as logic
import ckan.logic.converters as converters
import ckan.lib.base as base

class ExampleIDatasetFormPlugin(plugins.SingletonPlugin,
        lib_plugins.DefaultDatasetForm):
    '''An example IDatasetForm CKAN plugin.

    Uses a tag vocabulary to add a custom metadata field to datasets.

    '''
    plugins.implements(plugins.IConfigurer, inherit=True)
    plugins.implements(plugins.IDatasetForm, inherit=True)

    def create_country_codes(self):
        '''Create country_codes vocab and tags, if they don't exist already.

        Note that you could also create the vocab and tags using CKAN's API,
        and once they are created you can edit them (e.g. to add and remove
        possible dataset country code values) using the API.

        '''
        user = logic.get_action('get_site_user')({
            'model': base.model, 'ignore_auth': True}, {})
        context = {'model': base.model, 'session': base.model.Session,
                'user': user['name']}
        try:
            data = {'id': 'country_codes'}
            logic.get_action('vocabulary_show')(context, data)
            logging.info("Example genre vocabulary already exists, skipping.")
        except logic.NotFound:
            logging.info("Creating vocab 'country_codes'")
            data = {'name': 'country_codes'}
            vocab = logic.get_action('vocabulary_create')(context, data)
            for tag in (u'uk', u'ie', u'de', u'fr', u'es'):
                logging.info(
                        "Adding tag {} to vocab 'country_codes'".format(tag))
                data = {'name': tag, 'vocabulary_id': vocab['id']}
                logic.get_action('tag_create')(context, data)

    def update_config(self, config):
        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        toolkit.add_template_directory(config, 'templates')

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return []

    def form_to_db_schema(self):
        schema = logic.schema.form_to_db_package_schema()

        # Add our custom country_code metadata field to the schema.
        schema.update({
                'country_code': [validators.ignore_missing,
                    converters.convert_to_tags('country_codes')]
                })

        return schema

    def db_to_form_schema(self):
        schema = logic.schema.db_to_form_package_schema()

        # Add our custom country_code metadata field to the schema.
        schema.update({
            'country_code': [
                converters.convert_from_tags('country_codes'),
                validators.ignore_missing]
            })

        return schema

    def setup_template_variables(self, context, data_dict=None):
        lib_plugins.DefaultDatasetForm.setup_template_variables(self, context,
                data_dict)

        # Create the country_codes vocab and tags, if they don't already exist.
        self.create_country_codes()

        # Add the list of available country codes, from the country_codes
        # vocab, to the template context.
        try:
            toolkit.c.country_codes = logic.get_action('tag_list')(
                    context, {'vocabulary_id': 'country_codes'})
        except logic.NotFound:
            toolkit.c.country_codes = None

    def check_data_dict(self, data_dict):
        # Here we could validate the data dict submitted by the user when
        # creating or editing a package, e.g. to validate the submitted
        # value of our custom metadata field, but in this example there is no
        # validation needed.
        pass
