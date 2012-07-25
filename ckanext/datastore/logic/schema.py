from ckan.lib.navl.validators import (not_empty,
                                      not_missing,
                                      empty,
                                      ignore)


def default_datastore_create_schema():
    # TODO: resource_id should have a resource_id_exists validator
    return {
        'resource_id': [not_missing, not_empty, unicode],
        'fields': [ignore],
        'records': [ignore],
        '__extras': [empty],
    }
