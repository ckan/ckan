import ckan.plugins.toolkit as tk

def check_access(context, data_dict):
    return {"success": False}

def get_auth_functions():
    return {
        'check_auth_statistical': check_access,
    }