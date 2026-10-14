from __future__ import annotations



from ckan.types import AuthResult, Context, DataDict





def help_show(context: Context, data_dict: DataDict) -> AuthResult:
    return {'success': True}

def status_show(context: Context, data_dict: DataDict) -> AuthResult:
    '''Show information about the site's configuration. Visible to all by default.'''
    return {'success': True}
