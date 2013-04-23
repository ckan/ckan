'''
Helper functions to be used in the auth check functions
'''

import ckan.logic as logic


def _get_object(context, data_dict, name, class_name):
    # return the named item if in the data_dict, or get it from
    # model.class_name
    try:
        return context[name]
    except KeyError:
        if not data_dict:
            data_dict = {}
        id = data_dict.get('id', None)
        key = '_OBJECT_STORE_%s__%s' % (name, id)
        # This is our cache key to prevent multiple database calls.  Perhaps
        # this is a bit too much magic but it feels quite self contained and
        # safer that the using current data_dict['id'] magic.
        try:
            return context[key]
        except KeyError:
            model = context['model']
            obj = getattr(model, class_name).get(id)
            if not obj:
                raise logic.NotFound
            # Save in case we need this again during the request
            context[key] = obj
            return obj


def get_related_object(context, data_dict=None):
    return _get_object(context, data_dict, 'related', 'Related')


def get_package_object(context, data_dict=None):
    return _get_object(context, data_dict, 'package', 'Package')


def get_resource_object(context, data_dict=None):
    return _get_object(context, data_dict, 'resource', 'Resource')


def get_group_object(context, data_dict=None):
    return _get_object(context, data_dict, 'group', 'Group')


def get_user_object(context, data_dict=None):
    return _get_object(context, data_dict, 'user_obj', 'User')
