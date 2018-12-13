# encoding: utf-8

from nose.tools import assert_equal

from ckan import model, __version__
from ckan.lib.create_test_data import CreateTestData
from ckan.tests.legacy import TestController as ControllerTestCase
from ckan.tests.legacy import url_for
from ckan.common import json

class TestUtil(ControllerTestCase):
    @classmethod
    def setup_class(cls):
        CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_munge_package_name(self):
        response = self.app.get(
            url=url_for(controller='api', action='munge_package_name', ver=2),
            params={'name': 'test name'},
            status=200,
        )
        assert_equal(response.body, '"test-name"')

    def test_munge_title_to_package_name(self):
        response = self.app.get(
            url=url_for(controller='api', action='munge_title_to_package_name', ver=2),
            params={'name': 'Test title'},
            status=200,
        )
        assert_equal(response.body, '"test-title"')

    def test_munge_tag(self):
        response = self.app.get(
            url=url_for(controller='api', action='munge_tag', ver=2),
            params={'name': 'Test subject'},
            status=200,
        )
        assert_equal(response.body, '"test-subject"')
