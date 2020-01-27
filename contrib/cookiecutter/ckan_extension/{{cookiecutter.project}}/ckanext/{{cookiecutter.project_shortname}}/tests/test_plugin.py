"""Tests for plugin.py."""

import pytest

from ckan.plugins import plugin_loaded

import ckanext.{{ cookiecutter.project_shortname }}.plugin as plugin


@pytest.mark.ckan_config('ckan.plugins', '{{cookiecutter.project_shortname}}')
@pytest.mark.usefixtures('with_plugins')
def test_plugin():
    assert plugin_loaded('{{cookiecutter.project_shortname}}')
