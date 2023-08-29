# -*- coding: utf-8 -*-
from __future__ import annotations

from ckan.types import Action, Context, DataDict

__all__ = [u"sleep", u"wake_up"]


def get_actions() -> dict[str, Action]:
    return {u"sleep": sleep, u"wake_up": wake_up}


def sleep(context: Context, data_dict: DataDict):
    pass


def wake_up(context: Context, data_dict: DataDict):
    pass
