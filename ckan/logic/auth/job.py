from __future__ import annotations



from ckan.types import AuthResult, Context, DataDict





def job_list(context: Context, data_dict: DataDict) -> AuthResult:
    '''List background jobs. Only sysadmins.'''
    return {'success': False}

def job_show(context: Context, data_dict: DataDict) -> AuthResult:
    '''Show background job. Only sysadmins.'''
    return {'success': False}

def job_clear(context: Context, data_dict: DataDict) -> AuthResult:
    '''Clear background jobs. Only sysadmins.'''
    return {'success': False}

def job_cancel(context: Context, data_dict: DataDict) -> AuthResult:
    '''Cancel a background job. Only sysadmins.'''
    return {'success': False}
