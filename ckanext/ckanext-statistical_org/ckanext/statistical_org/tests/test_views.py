"""Tests for views.py."""

import pytest

import ckanext.statistical_org.validators as validators


import ckan.plugins.toolkit as tk


@pytest.mark.ckan_config("ckan.plugins", "statistical_org")
@pytest.mark.usefixtures("with_plugins")
def test_statistical_org_blueprint(app, reset_db):
    resp = app.get(tk.h.url_for("statistical_org.page"))
    assert resp.status_code == 200
    assert resp.body == "Hello, statistical_org!"
