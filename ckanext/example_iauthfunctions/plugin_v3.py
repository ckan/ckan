# encoding: utf-8
from __future__ import annotations

from ckan.types import (
    AuthFunction, AuthResult, Context, ContextValidator, DataDict)
from typing import Optional, cast
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


def group_create(
        context: Context, data_dict: Optional[DataDict] = None) -> AuthResult:
    # Get the user name of the logged-in user.
    user_name: str = context['user']

    # Get a list of the members of the 'curators' group.
    members = toolkit.get_action('member_list')(
        {},
        {'id': 'curators', 'object_type': 'user'})

    # 'members' is a list of (user_id, object_type, capacity) tuples, we're
    # only interested in the user_ids.
    member_ids = [member_tuple[0] for member_tuple in members]

    # We have the logged-in user's user name, get their user id.
    convert_user_name_or_id_to_id = cast(
        ContextValidator,
        toolkit.get_converter('convert_user_name_or_id_to_id'))
    user_id = convert_user_name_or_id_to_id(user_name, context)

    # Finally, we can test whether the user is a member of the curators group.
    if user_id in member_ids:
        return {'success': True}
    else:
        return {'success': False,
                'msg': 'Only curators are allowed to create groups'}


class ExampleIAuthFunctionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAuthFunctions)

    def get_auth_functions(self) -> dict[str, AuthFunction]:
        return {'group_create': group_create}
