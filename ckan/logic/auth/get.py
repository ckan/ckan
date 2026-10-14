# encoding: utf-8

import ckan.logic as logic
from ckan.common import _
from ckan.types import AuthResult, Context, DataDict


@logic.auth_allow_anonymous_access
def sysadmin(context: Context, data_dict: DataDict) -> AuthResult:
    ''' This is a pseudo check if we are a sysadmin all checks are true '''
    return {'success': False, 'msg': _('Not authorized')}
