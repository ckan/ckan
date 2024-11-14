import ckan.plugins.toolkit as tk

def tracking_access(context, data_dict):
    return {"success": False}

def get_auth_functions():
    return {
        'tracking_access': tracking_access,
    }