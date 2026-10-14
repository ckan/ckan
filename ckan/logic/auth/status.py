from __future__ import annotations

import ckan.logic as logic



from ckan.types import AuthResult, Context, DataDict





@logic.auth_allow_anonymous_access
def help_show(context: Context, data_dict: DataDict) -> AuthResult:
    return {'success': True}

@logic.auth_allow_anonymous_access
def status_show(context: Context, data_dict: DataDict) -> AuthResult:
    '''Show information about the site's configuration. Visible to all by default.'''
    return {'success': True}
