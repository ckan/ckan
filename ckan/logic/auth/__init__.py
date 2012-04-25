'''
Helper functions to be used in the auth check functions
'''

from ckan.logic import NotFound

def _get_object(context, data_dict, name, class_name):
    # return the named item if in the data_dict, or get it from
    # model.class_name
    if not name in context:
        model = context['model']
        id = data_dict.get('id', None)
        obj = getattr(model, class_name).get(id)
        if not obj:
            raise NotFound
    else:
        obj = context[name]
    return obj

def get_related_object(context, data_dict = {}):
    return _get_object(context, data_dict, 'related', 'Related')

def get_package_object(context, data_dict = {}):
    return _get_object(context, data_dict, 'package', 'Package')

def get_resource_object(context, data_dict={}):
    return _get_object(context, data_dict, 'resource', 'Resource')

def get_group_object(context, data_dict={}):
    return _get_object(context, data_dict, 'group', 'Group')

def get_user_object(context, data_dict={}):
    return _get_object(context, data_dict, 'user_obj', 'User')

def get_authorization_group_object(context, data_dict={}):
    return _get_object(context, data_dict, 'authorization_group',
                       'AuthorizationGroup')
