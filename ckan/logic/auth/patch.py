# encoding: utf-8

import ckan.authz as authz
from ckan.types import Context, DataDict, AuthResult


def package_patch(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('package_update', context, data_dict)


def resource_patch(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('resource_update', context, data_dict)


def group_patch(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('group_update', context, data_dict)


def organization_patch(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('organization_update', context, data_dict)


def user_patch(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized('user_update', context, data_dict)
