import ckan.controllers.group as group


class OrganizationController(group.GroupController):
    ''' The organization controller is pretty much just the group
    controller. It has a few templates defined that are different and sets
    the group_type to organization so that the group controller knows that
    it is in fact the organization controller.  All the main logical
    differences are therefore in the group controller.

    The main differences the group controller provides for organizations are
    a few wrapper functions that swap organization for group when rendering
    templates, redirecting or calling logic actions '''

    # this makes us use organization actions
    group_type = 'organization'

    def _group_form(self, group_type=None):
        return 'organization/new_organization_form.html'

    def _form_to_db_schema(self, group_type=None):
        return group.lookup_group_plugin(group_type).form_to_db_schema()

    def _db_to_form_schema(self, group_type=None):
        '''This is an interface to manipulate data from the database
        into a format suitable for the form (optional)'''
        pass

    def _setup_template_variables(self, context, data_dict, group_type=None):
        pass

    def _new_template(self, group_type):
        return 'organization/new.html'

    def _about_template(self, group_type):
        return 'organization/about.html'

    def _index_template(self, group_type):
        return 'organization/index.html'

    def _admins_template(self, group_type):
        return 'organization/admins.html'

    def _bulk_process_template(self, group_type):
        return 'organization/bulk_process.html'

    def _read_template(self, group_type):
        return 'organization/read.html'

    def _history_template(self, group_type):
        return group.lookup_group_plugin(group_type).history_template()

    def _edit_template(self, group_type):
        return 'organization/edit.html'

    def _activity_template(self, group_type):
        return 'organization/activity_stream.html'

    def _guess_group_type(self, expecting_name=False):
        return 'organization'
