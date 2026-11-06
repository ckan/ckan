"""Tests for authorization in ckan/logic/auth/tag.py."""

import pytest

from ckan import model
from ckan.tests import factories, helpers


@pytest.mark.parametrize("func", ["tag_search"])
def test_anonymous_can_call_get_method(func):
    user = factories.User()
    context = {"user": "", "model": model}
    assert helpers.call_auth(func, context, id=user["id"])
