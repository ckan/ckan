import ckan.plugins.toolkit as tk

def user_check(context, data_dict):
    user = context.get('user')
    if not user:
        raise tk.NotAuthorized("You don't have access to use this function")

    return {"success": True}

def get_auth_functions():
    return {
        'user_check': user_check,
    }