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

    def _guess_group_type(self, expecting_name=False):
        return 'organization'
