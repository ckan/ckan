import ckan.plugins.toolkit as tk

def user_check(context, data_dict):
    return {"success": False}


def get_auth_functions():
    return {
        'user_check': user_check,
    }