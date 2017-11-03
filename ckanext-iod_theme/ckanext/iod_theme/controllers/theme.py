import ckan.controllers.group as group

class ThemeController(group.GroupController):
    group_types = ['group']

    def _guess_group_type(self, expecting_name=False):
        return 'group'