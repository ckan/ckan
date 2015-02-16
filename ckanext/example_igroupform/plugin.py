import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


class ExampleigroupformPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IGroupForm, inherit=True)
    plugins.implements(plugins.IRoutes, inherit=True)

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')

    controller_name = 'ckanext.example_igroupform.controller' + \
                      ':ExampleigroupformController'
    def before_map(self, map):
        map.connect('example_group_index',
                    '/example_group',
                    controller=controller_name,
                    action='index')
        map.connect('example_group_new',
                    '/example_group/new',
                    controller=controller_name,
                    action='new')
        map.connect('example_group_edit',
                    '/example_group/edit',
                    controller=controller_name,
                    action='edit')
        return map

    def after_map(self, map):
        return map

    def is_fallback(self):
        return False

    def group_types(self):
        return ['example_group']

    def group_form(self):
        return 'new_example_group_form.html'

    def new_template(self):
        return 'new.html'

    def read_template(self):
        return 'read.html'

    def index_template(self):
        return 'index.html'

    def edit_template(self):
        return 'edit.html'

    def form_to_db_schema_options(self, options):
        ''' This allows us to select different schemas for different
        purpose eg via the web interface or via the api or creation vs
        updating. It is optional and if not available form_to_db_schema
        should be used.
        If a context is provided, and it contains a schema, it will be
        returned.
        '''
        schema = options.get('context', {}).get('schema', None)
        if schema:
            return schema

        if options.get('api'):
            if options.get('type') == 'create':
                return self.form_to_db_schema_api_create()
            else:
                return self.form_to_db_schema_api_update()
        else:
            return self.form_to_db_schema()

    def form_to_db_schema_api_create(self):
        schema = super(NodePlugin, self).form_to_db_schema_api_create()
        schema = self._modify_group_schema(schema)
        return schema

    def form_to_db_schema_api_update(self):
        schema = super(NodePlugin, self).form_to_db_schema_api_update()
        schema = self._modify_group_schema(schema)
        return schema

    def form_to_db_schema(self):
        schema = super(NodePlugin, self).form_to_db_schema()
        schema = self._modify_group_schema(schema)
        return schema

    def _modify_group_schema(self, schema):
        _convert_to_extras = toolkit.get_converter('convert_to_extras')
        _ignore_missing = toolkit.get_validator('ignore_missing')

        default_validators = [_ignore_missing, _convert_to_extras]
        schema.update({ 'new_field': default_validators })
        return schema

    def db_to_form_schema(self):
        _convert_from_extras = toolkit.get_converter('convert_from_extras')
        _ignore_missing = toolkit.get_validator('ignore_missing')

        schema = super(NodePlugin, self).form_to_db_schema()

        default_validators = [_convert_from_extras, _ignore_missing]
        schema.update({ 'new_field': default_validators })
        return schema
