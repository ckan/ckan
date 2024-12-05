"""Tests for validators.py."""

import pytest

import ckan.plugins.toolkit as tk

from ckanext.statistical_org.logic import validators


def test_statistical_org_reauired_with_valid_value():
    assert validators.statistical_org_required("value") == "value"


def test_statistical_org_reauired_with_invalid_value():
    with pytest.raises(tk.Invalid):
        validators.statistical_org_required(None)
