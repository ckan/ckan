import ckan.controllers.group as group

class OrganizationController(group.GroupController):

    # this makes us use organization actions
    group_type = 'organization'

    def _group_form(self, group_type=None):
        return 'organization/new_organization_form.html'

    def _form_to_db_schema(self, group_type=None):
        return lookup_group_plugin(group_type).form_to_db_schema()

    def _db_to_form_schema(self, group_type=None):
        '''This is an interface to manipulate data from the database
        into a format suitable for the form (optional)'''
        return lookup_group_plugin(group_type).db_to_form_schema()

    def _setup_template_variables(self, context, data_dict, group_type=None):
        pass

    def _new_template(self, group_type):
        return 'organization/new.html'

    def _index_template(self, group_type):
        return 'organization/index.html'

    def _read_template(self, group_type):
        return 'organization/read.html'

    def _history_template(self, group_type):
        return lookup_group_plugin(group_type).history_template()

    def _edit_template(self, group_type):
        return 'organization/edit.html'

    def _guess_group_type(self, expecting_name=False):
        return 'organization'
