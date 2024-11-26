"""Tests for validators.py."""

import pytest

import ckan.plugins.toolkit as tk

from ckanext.tracking_datatypes.logic import validators


def test_tracking_datatypes_reauired_with_valid_value():
    assert validators.tracking_datatypes_required("value") == "value"


def test_tracking_datatypes_reauired_with_invalid_value():
    with pytest.raises(tk.Invalid):
        validators.tracking_datatypes_required(None)
