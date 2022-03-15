"""Tests for validators.py."""

import pytest

import ckan.plugins.toolkit as tk

from ckanext.{{cookiecutter.project_shortname}}.logic import validators


def test_{{cookiecutter.project_shortname}}_reauired_with_valid_value():
    assert validators.{{
        cookiecutter.project_shortname}}_required("value") == "value"


def test_{{cookiecutter.project_shortname}}_reauired_with_invalid_value():
    with pytest.raises(tk.Invalid):
        validators.{{cookiecutter.project_shortname}}_required(None)
