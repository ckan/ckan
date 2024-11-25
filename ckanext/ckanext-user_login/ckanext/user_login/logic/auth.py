import ckan.plugins.toolkit as tk

def login_activity_show(context, data_dict):
    return {"success": False}


def get_auth_functions():
    return {
        'login_activity_show': login_activity_show,
    }