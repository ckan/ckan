from __future__ import annotations



from ckan.types import AuthResult, Context, DataDict





def config_option_show(context: Context, data_dict: DataDict) -> AuthResult:
    '''Show runtime-editable configuration option. Only sysadmins.'''
    return {'success': False}

def config_option_list(context: Context, data_dict: DataDict) -> AuthResult:
    '''List runtime-editable configuration options. Only sysadmins.'''
    return {'success': False}

def config_option_update(context: Context, data_dict: DataDict) -> AuthResult:
    '''Update the runtime-editable configuration options

       Only sysadmins can do it
    '''
    return {'success': False}
