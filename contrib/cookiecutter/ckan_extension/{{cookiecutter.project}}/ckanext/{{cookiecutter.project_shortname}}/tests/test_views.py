"""Tests for views.py."""

import pytest

import ckanext.{{cookiecutter.project_shortname}}.validators as validators


import ckan.plugins.toolkit as tk


@pytest.mark.ckan_config("ckan.plugins", "{{cookiecutter.project_shortname}}")
@pytest.mark.usefixtures("with_plugins")
def test_{{cookiecutter.project_shortname}}_blueprint(app, reset_db):
    resp = app.get(tk.h.url_for("{{cookiecutter.project_shortname}}.page"))
    assert resp.status_code == 200
    assert resp.body == "Hello, {{cookiecutter.project_shortname}}!"
