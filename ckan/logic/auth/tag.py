from __future__ import annotations

import ckan.authz as authz
import ckan.logic as logic
from ckan.types import AuthResult, Context, DataDict


@logic.auth_allow_anonymous_access
def vocabulary_list(context: Context, data_dict: DataDict) -> AuthResult:
    # List of all vocabularies are visible by default
    return {"success": True}


@logic.auth_allow_anonymous_access
def tag_list(context: Context, data_dict: DataDict) -> AuthResult:
    # Tags list is visible by default
    return {"success": True}


@logic.auth_allow_anonymous_access
def vocabulary_show(context: Context, data_dict: DataDict) -> AuthResult:
    # Allow viewing of vocabs by default
    return {"success": True}


@logic.auth_allow_anonymous_access
def tag_show(context: Context, data_dict: DataDict) -> AuthResult:
    # No authz check in the logic function
    return {"success": True}


@logic.auth_allow_anonymous_access
def tag_autocomplete(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized("tag_list", context, data_dict)


@logic.auth_allow_anonymous_access
def tag_search(context: Context, data_dict: DataDict) -> AuthResult:
    """Check if tag search is allowed.
    Allowed for all by default."""
    return {"success": True}


def vocabulary_create(context: Context, data_dict: DataDict) -> AuthResult:
    # sysadmins only
    return {"success": False}


def tag_create(context: Context, data_dict: DataDict) -> AuthResult:
    # sysadmins only
    return {"success": False}


def vocabulary_update(context: Context, data_dict: DataDict) -> AuthResult:
    # sysadmins only
    return {"success": False}


def vocabulary_delete(context: Context, data_dict: DataDict) -> AuthResult:
    # sysadmins only
    return {"success": False}


def tag_delete(context: Context, data_dict: DataDict) -> AuthResult:
    # sysadmins only
    return {"success": False}
