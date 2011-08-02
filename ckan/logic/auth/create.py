#This will be check_access_old
from ckan.logic import check_access

def package_create(context, data_dict):
    model = context['model']

    return {'success':  check_access(model.System(), model.Action.PACKAGE_CREATE, context)}

def resource_create(context, data_dict):
    return {'success': False, 'msg': 'Not implemented yet in the auth refactor'}

def package_relationship_create(context, data_dict):
    return {'success': False, 'msg': 'Not implemented yet in the auth refactor'}

def group_create(context, data_dict):
    return {'success': False, 'msg': 'Not implemented yet in the auth refactor'}

def rating_create(context, data_dict):
    return {'success': False, 'msg': 'Not implemented yet in the auth refactor'}

## Modifications for rest api

def package_create_rest(context, data_dict):
    return {'success': False, 'msg': 'Not implemented yet in the auth refactor'}

def group_create_rest(context, data_dict):
    return {'success': False, 'msg': 'Not implemented yet in the auth refactor'}

