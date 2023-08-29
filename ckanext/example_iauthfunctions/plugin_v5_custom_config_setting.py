# encoding: utf-8

from typing import Optional
from ckan.types import AuthResult, Context, DataDict

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.config.declaration import Declaration, Key


def group_create(
        context: Context,
        data_dict: Optional[DataDict] = None) -> AuthResult:

    # Get the value of the ckan.iauthfunctions.users_can_create_groups
    # setting from the CKAN config file as a string, or False if the setting
    # isn't in the config file.
    users_can_create_groups = toolkit.config.get(
        'ckan.iauthfunctions.users_can_create_groups')

    if users_can_create_groups:
        return {'success': True}
    else:
        return {'success': False,
                'msg': 'Only sysadmins can create groups'}


class ExampleIAuthFunctionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IConfigDeclaration)

    def get_auth_functions(self):
        return {'group_create': group_create}

    # IConfigDeclaration

    def declare_config_options(self, declaration: Declaration, key: Key):
        declaration.declare_bool(
            key.ckan.iauthfunctions.users_can_create_groups)
