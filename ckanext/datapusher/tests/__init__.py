# encoding: utf-8
from ckan.tests import factories


def get_api_token() -> str:
    return factories.SysadminWithToken()["sysadmin"]
