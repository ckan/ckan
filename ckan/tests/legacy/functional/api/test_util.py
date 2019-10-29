# encoding: utf-8

from nose.tools import assert_equal
import pytest
from ckan import model
from ckan.lib.create_test_data import CreateTestData
from ckan.tests.legacy import TestController as ControllerTestCase
from ckan.tests.legacy import url_for


@pytest.fixture(autouse=True)
def initial_data(clean_db):
    CreateTestData.create()


def test_munge_package_name(app):
    response = app.get(
        url=url_for(controller="api", action="munge_package_name", ver=2),
        params={"name": "test name"},
        status=200,
    )
    assert response.body == '"test-name"'


def test_munge_title_to_package_name(app):
    response = app.get(
        url=url_for(
            controller="api", action="munge_title_to_package_name", ver=2
        ),
        params={"name": "Test title"},
        status=200,
    )
    assert response.body == '"test-title"'


def test_munge_tag(app):
    response = app.get(
        url=url_for(controller="api", action="munge_tag", ver=2),
        params={"name": "Test subject"},
        status=200,
    )
    assert response.body == '"test-subject"'
