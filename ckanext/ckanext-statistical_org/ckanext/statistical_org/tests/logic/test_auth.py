"""Tests for auth.py."""

import pytest

import ckan.tests.factories as factories
import ckan.tests.helpers as test_helpers
import ckan.model as model


@pytest.mark.ckan_config("ckan.plugins", "statistical_org")
@pytest.mark.usefixtures("with_request_context", "with_plugins", "clean_db")
def test_statistical_org_get_sum():
    user = factories.User()
    context = {
        "user": user["name"],
        "model": model
    }
    assert test_helpers.call_auth(
        "statistical_org_get_sum", context=context)
