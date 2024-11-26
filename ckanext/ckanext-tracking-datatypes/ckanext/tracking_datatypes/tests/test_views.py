"""Tests for views.py."""

import pytest

import ckanext.tracking_datatypes.validators as validators


import ckan.plugins.toolkit as tk


@pytest.mark.ckan_config("ckan.plugins", "tracking_datatypes")
@pytest.mark.usefixtures("with_plugins")
def test_tracking_datatypes_blueprint(app, reset_db):
    resp = app.get(tk.h.url_for("tracking_datatypes.page"))
    assert resp.status_code == 200
    assert resp.body == "Hello, tracking_datatypes!"
