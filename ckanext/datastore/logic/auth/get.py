import ckan.plugins as p


def datastore_search(context, data_dict):
    data_dict['id'] = data_dict.get('resource_id')
    user = context.get('user')

    authorized = p.toolkit.check_access('resource_update', context, data_dict)

    if not authorized:
        return {'success': False,
                'msg': p.toolkit._('User %s not authorized to read edit %s') %\
                    (str(user), data_dict['id'])}
    else:
        return {'success': True}
