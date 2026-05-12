# encoding: utf-8

'''
Helper functions to be used in the auth check functions
'''

from typing import Any, Optional, overload
from typing_extensions import Literal

import ckan.logic as logic
import ckan.authz as authz
from ckan import model
from ckan.types import Context, AuthResult, DataDict


@overload
def _get_object(context: Context,
                data_dict: Optional[DataDict], name: str,
                class_name: Literal['Package']) -> model.Package:
    ...


@overload
def _get_object(context: Context,
                data_dict: Optional[DataDict], name: str,
                class_name: Literal['Resource']) -> model.Resource:
    ...


@overload
def _get_object(context: Context,
                data_dict: Optional[DataDict], name: str,
                class_name: Literal['Group']) -> model.Group:
    ...


@overload
def _get_object(context: Context,
                data_dict: Optional[DataDict], name: str,
                class_name: Literal['User']) -> model.User:
    ...


def _get_object(context: Context,
                data_dict: Optional[DataDict], name: str,
                class_name: str) -> Any:
    # return the named item from model.class_name
    if not data_dict:
        data_dict = {}
    id = data_dict.get('id', None)
    if not id:
        raise logic.ValidationError({
            "message": 'Missing id, can not get {0} object'.format(
                class_name)})
    obj = getattr(model, class_name).get(id)
    if not obj:
        raise logic.NotFound
    return obj


def get_package_object(
        context: Context,
        data_dict: Optional[DataDict] = None) -> model.Package:
    return _get_object(context, data_dict, 'package', 'Package')


def get_resource_object(
        context: Context,
        data_dict: Optional[DataDict] = None) -> model.Resource:
    return _get_object(context, data_dict, 'resource', 'Resource')


def get_group_object(
        context: Context,
        data_dict: Optional[DataDict] = None) -> model.Group:
    return _get_object(context, data_dict, 'group', 'Group')


def get_user_object(
        context: Context,
        data_dict: Optional[DataDict] = None) -> model.User:
    return _get_object(context, data_dict, 'user_obj', 'User')


def restrict_anon(context: Context) -> AuthResult:
    if authz.auth_is_anon_user(context):
        return {'success': False}
    else:
        return {'success': True}
