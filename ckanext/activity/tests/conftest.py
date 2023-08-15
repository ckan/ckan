# -*- coding: utf-8 -*-

import pytest
from pytest_factoryboy import register

from ckan import model
import ckan.plugins
from ckan.tests import helpers, factories
from ckan.cli.db import _run_migrations
from ckan.tests.factories import CKANFactory
from ckanext.activity.model import Activity

from sqlalchemy import inspect


@register
class ActivityFactory(CKANFactory):
    """A factory class for creating CKAN activity objects."""

    class Meta:
        model = Activity
        action = "activity_create"


@pytest.fixture(autouse=False, scope="class")
def apply_activity_migrations():
    plugin = "activity"

    factories.fake.unique.clear()
    helpers.reset_db()

    if not ckan.plugins.plugin_loaded(plugin):
        ckan.plugins.load(plugin)

    _run_migrations(plugin, version="head", forward=True)

    columns = inspect(model.Session.bind).get_columns("activity")
    assert "permission_labels" in [c["name"] for c in columns]

    yield

    if ckan.plugins.plugin_loaded(plugin):
        ckan.plugins.unload(plugin)
