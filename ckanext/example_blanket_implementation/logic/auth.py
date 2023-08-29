# -*- coding: utf-8 -*-

from ckan.types import Context, DataDict

__all__ = [u"sleep", u"wake_up"]


def sleep(context: Context, data_dict: DataDict):
    pass


def wake_up(context: Context, data_dict: DataDict):
    pass


# not exported
def lie_down(context: Context, data_dict: DataDict):
    pass
