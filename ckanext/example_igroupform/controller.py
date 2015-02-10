import ckan.controllers.group as group

class ExampleigroupformController(group.GroupController):
    group_type = 'example_group'

    def _guess_group_type(self, expecting_name=False):
        return 'example_group'
