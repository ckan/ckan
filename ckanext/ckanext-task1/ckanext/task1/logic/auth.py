import ckan.plugins.toolkit as tk

def tracking_urls_and_counts1(context, data_dict):
    return {"success": True}

def get_auth_functions():
    return {
        'tracking_urls_and_counts1': tracking_urls_and_counts1,
    }