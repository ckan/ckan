import ckan.plugins as p


def datastore_create(context, data_dict):
    model = context['model']
    user = context['user']
    userobj = model.User.get(user)

    if userobj:
        return {'success': True}
    return {'success': False,
            'msg': p.toolkit._('You must be logged in to use the datastore.')}
