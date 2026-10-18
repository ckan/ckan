"""Tests for authorization in ckan/logic/auth/term_translation.py."""

import pytest
import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers



@pytest.mark.parametrize("func", ["term_translation_show"])
def test_anonymous_can_call_get_method(func):
    user = factories.User()
    context = {"user": "", "model": model}
    assert helpers.call_auth(func, context, id=user["id"])
