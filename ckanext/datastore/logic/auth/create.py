import ckan.plugins as p
import ckan.logic as logic
from ckan.lib.base import _

_check_access = logic.check_access

def datastore_create(context, data_dict):
    data_dict['id'] = data_dict.get('resource_id')
    user = context.get('user')

    authorized = _check_access('resource_update', context, data_dict)

    if not authorized:
        return {'success': False,
                'msg': _('User %s not authorized to read edit %s') % (str(user), data_dict['id'])}
    else:
        return {'success': True}
