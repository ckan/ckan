from __future__ import annotations

from typing import Any
from ckan.types import Context


def file_search(context: Context, data_dict: dict[str, Any]): ...


def file_create(context: Context, data_dict: dict[str, Any]): ...


def file_delete(context: Context, data_dict: dict[str, Any]): ...


def file_show(context: Context, data_dict: dict[str, Any]): ...


def file_download(context: Context, data_dict: dict[str, Any]): ...


def file_rename(context: Context, data_dict: dict[str, Any]): ...


def file_pin(context: Context, data_dict: dict[str, Any]): ...


def file_unpin(context: Context, data_dict: dict[str, Any]): ...


def file_ownership_transfer(context: Context, data_dict: dict[str, Any]): ...


def file_owner_scan(context: Context, data_dict: dict[str, Any]): ...
