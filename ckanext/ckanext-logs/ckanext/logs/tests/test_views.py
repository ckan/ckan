"""Tests for views.py."""

import pytest

import ckanext.logs.validators as validators


import ckan.plugins.toolkit as tk


@pytest.mark.ckan_config("ckan.plugins", "logs")
@pytest.mark.usefixtures("with_plugins")
def test_logs_blueprint(app, reset_db):
    resp = app.get(tk.h.url_for("logs.page"))
    assert resp.status_code == 200
    assert resp.body == "Hello, logs!"
