"""Tests for validators.py."""

import pytest

import ckan.plugins.toolkit as tk

from ckanext.logs.logic import validators


def test_logs_reauired_with_valid_value():
    assert validators.logs_required("value") == "value"


def test_logs_reauired_with_invalid_value():
    with pytest.raises(tk.Invalid):
        validators.logs_required(None)
