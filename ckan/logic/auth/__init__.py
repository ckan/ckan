'''
Helper functions to be used in the auth check functions
'''

from ckan.logic import NotFound

def get_package_object(context, data_dict = {}):
    if not 'package' in context:
        model = context['model']
        id = data_dict.get('id',None)
        package = model.Package.get(id)
        if not package:
            raise NotFound
    else:
        package = context['package']

    return package

def get_resource_object(context, data_dict={}):
    if not 'resource' in context:
        model = context['model']
        id = data_dict.get('id',None)
        resource = model.Resource.get(id)
        if not resource:
            raise NotFound
    else:
        resource = context['resource']

    return resource

def get_group_object(context, data_dict={}):
    if not 'group' in context:
        model = context['model']
        id = data_dict.get('id',None)
        group = model.Group.get(id)
        if not group:
            raise NotFound
    else:
        group = context['group']

    return group

def get_user_object(context, data_dict={}):
    if not 'user_obj' in context:
        model = context['model']
        id = data_dict.get('id',None)
        user_obj = model.User.get(id)
        if not user_obj:
            raise NotFound
    else:
        user_obj = context['user_obj']

    return user_obj

def get_authorization_group_object(context, data_dict={}):
    if not 'authorization_group' in context:
        model = context['model']
        id = data_dict.get('id',None)
        # Auth groups don't have get method
        authorization_group = model.Session.query(model.AuthorizationGroup).filter(model.AuthorizationGroup.id==id).first()
        if not authorization_group:
            raise NotFound
    else:
        authorization_group = context['authorization_group']

    return authorization_group
