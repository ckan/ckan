import re

import ckan.controllers.group as group


class OrganizationController(group.GroupController):
    ''' The organization controller is for Groups of type 'organization'. It
    works the same as the group controller apart from:
    * templates and logic action/auth functions are sometimes customized
      (switched using _replace_group_org)
    * 'bulk_process' action only works for organizations

    Nearly all the code for both is in the GroupController (for simplicity?).
    '''

    group_types = ['organization']

    def _guess_group_type(self, expecting_name=False):
        return 'organization'

    def _replace_group_org(self, string):
        ''' substitute organization for group if this is an org'''
        return re.sub('^group', 'organization', string)
