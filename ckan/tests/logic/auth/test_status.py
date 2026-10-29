"""Tests for authorization in ckan/logic/auth/status.py."""


from ckan import model
from ckan.tests import helpers


def test_status_show_is_visible_to_anonymous():
    context = {"user": "", "model": model}
    assert helpers.call_auth("status_show", context)
