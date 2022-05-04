# encoding: utf-8
from __future__ import annotations

from typing import Any
from ckan.types import AuthResult, Context
import ckanext.datastore.logic.auth as auth


def datapusher_submit(
        context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return auth.datastore_auth(context, data_dict)


def datapusher_status(
        context: Context, data_dict: dict[str, Any]) -> AuthResult:
    return auth.datastore_auth(context, data_dict)
