# encoding: utf-8

import ckan.logic as logic
import ckan.authz as authz
from ckan import model
from ckan.logic.auth import get_group_object
from ckan.logic.auth import get_resource_object
from ckan.common import _
from ckan.types import Context, DataDict, AuthResult


def _check_unfollow_auth(context: Context) -> bool:
    if not context.get('user'):
        return False

    userobj = model.User.get(context['user'])
    if not userobj:
        return False

    return True
