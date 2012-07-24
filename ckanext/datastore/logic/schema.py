from ckan.lib.navl.validators import (not_empty,
                                      not_missing,
                                      empty,
                                      ignore_missing,
                                      ignore)


def default_fields_schema():
    return {
        'id': [not_missing, not_empty, unicode],
        'type': [not_missing, not_empty, unicode],
        'label': [ignore_missing, unicode],
    }


def default_datastore_create_schema():
    return {
        'resource_id': [not_missing, not_empty, unicode],
        'fields': default_fields_schema(),
        'records': [ignore],
        '__extras': [empty],
    }
