'''API functions for partial updates of existing data in CKAN'''

import ckan.logic.action.update as _update
from ckan.logic import (
    get_action as _get_action,
    check_access as _check_access,
    get_or_bust as _get_or_bust,
)


def package_patch(context, data_dict):
    '''Patch a dataset (package).

    The difference between the update and patch methods is that the patch will
    perform an update of the provided parameters, while leaving all other
    parameters unchanged, whereas the update methods deletes all parameters
    not explicitly provided in the data_dict

    You must be authorized to edit the dataset and the groups that it belongs
    to.

    '''

    _check_access('package_patch', context, data_dict)

    show_context = {
        'model': context['model'],
        'session': context['session'],
        'user': context['user'],
        'auth_user_obj': context['auth_user_obj'],
        }

    package_dict = _get_action('package_show')(
        show_context,
        {'id': _get_or_bust(data_dict, 'id')})

    patched = dict(package_dict.items() + data_dict.items())
    return _update.package_update(context, patched)
