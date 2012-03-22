import os, logging
from ckan.logic import NotAuthorized
from ckan.logic.schema import group_form_schema
from ckan.lib.base import c, model, abort, request
from ckan.lib.base import redirect, _, config, h
from ckan.lib.navl.dictization_functions import DataError
from ckan.plugins import IGroupForm, IConfigurer
from ckan.plugins import implements, SingletonPlugin
from ckan.logic import check_access

from ckan.lib.navl.validators import (ignore_missing,
                                      not_empty,
                                      empty,
                                      ignore,
                                      keep_extras,
                                     )

log = logging.getLogger(__name__)

class OrganizationForm(SingletonPlugin):
    """
    This plugin implements an IGroupForm for form associated with a
    organization group. ``IConfigurer`` is used to add the local template
    path and the IGroupForm supplies the custom form.
    """
    implements(IGroupForm, inherit=True)
    implements(IConfigurer, inherit=True)

    def update_config(self, config):
        """
        This IConfigurer implementation causes CKAN to look in the
        ```templates``` directory when looking for the group_form()
        """
        here = os.path.dirname(__file__)
        rootdir = os.path.dirname(os.path.dirname(here))
        template_dir = os.path.join(rootdir, 'ckanext',
                                    'organizations', 'templates')
        config['extra_template_paths'] = ','.join([template_dir,
                config.get('extra_template_paths', '')])

        # Override /group/* as the default groups urls
        config['ckan.default.group_type'] = 'organization'

    def new_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the new page
        """
        return 'organization_new.html'

    def index_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the index page
        """
        return 'organization_index.html'


    def read_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the read page
        """
        return 'organization_read.html'

    def history_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the read page
        """
        return 'organization_history.html'


    def group_form(self):
        """
        Returns a string representing the location of the template to be
        rendered.  e.g. "forms/group_form.html".
        """
        return 'organization_form.html'

    def group_types(self):
        """
        Returns an iterable of group type strings.

        If a request involving a group of one of those types is made, then
        this plugin instance will be delegated to.

        There must only be one plugin registered to each group type.  Any
        attempts to register more than one plugin instance to a given group
        type will raise an exception at startup.
        """
        return ["organization"]

    def is_fallback(self):
        """
        Returns true iff this provides the fallback behaviour, when no other
        plugin instance matches a group's type.

        As this is not the fallback controller we should return False.  If
        we were wanting to act as the fallback, we'd return True
        """
        return False

    def form_to_db_schema(self):
        """
        Returns the schema for mapping group data from a form to a format
        suitable for the database.
        """
        return group_form_schema()

    def db_to_form_schema(self):
        """
        Returns the schema for mapping group data from the database into a
        format suitable for the form (optional)
        """
        return {}

    def check_data_dict(self, data_dict):
        """
        Check if the return data is correct.

        raise a DataError if not.
        """

    def setup_template_variables(self, context, data_dict):
        """
        Add variables to c just prior to the template being rendered. We should
        use the available groups for the current user, but should be optional
        in case this is a top level group
        """
        c.user_groups = c.userobj.get_groups('organization')
        local_ctx = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}

        try:
            check_access('group_create', local_ctx)
            c.is_superuser_or_groupadmin = True
        except NotAuthorized:
            c.is_superuser_or_groupadmin = False

        if 'group' in context:
            group = context['group']
            # Only show possible groups where the current user is a member
            c.possible_parents = c.userobj.get_groups('organization', 'admin')

            c.parent = None
            grps = group.get_groups('organization')
            if grps:
                c.parent = grps[0]
            c.users = group.members_of_type(model.User)
