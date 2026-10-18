"""Tests for authorization in ckan/logic/auth/status.py."""

import pytest

import ckan.model as model
import ckan.tests.helpers as helpers


@pytest.mark.usefixtures("non_clean_db")
def test_status_show_is_visible_to_anonymous():
    context = {"user": "", "model": model}
    assert helpers.call_auth("status_show", context)
