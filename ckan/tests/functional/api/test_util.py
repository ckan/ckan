from nose.tools import assert_equal

from ckan import model, __version__
from ckan.lib.create_test_data import CreateTestData
from ckan.tests import TestController as ControllerTestCase
from ckan.tests import url_for
from ckan.common import json

class TestUtil(ControllerTestCase):
    @classmethod
    def setup_class(cls):
        CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_package_slug_invalid(self):
        response = self.app.get(
            url=url_for(controller='api', action='is_slug_valid', ver=2),
            params={
               'type': u'package',
               'slug': u'edit',
            },
            status=200,
        )
        assert_equal(response.body, '{"valid": false}')
        assert_equal(response.header('Content-Type'), 'application/json;charset=utf-8')

        response = self.app.get(
            url=url_for(controller='api', action='is_slug_valid', ver=2),
            params={
               'type': u'package',
               'slug': u'new',
            },
            status=200,
        )
        assert_equal(response.body, '{"valid": false}')
        assert_equal(response.header('Content-Type'), 'application/json;charset=utf-8')

    def test_package_slug_valid(self):
        response = self.app.get(
            url=url_for(controller='api', action='is_slug_valid', ver=2),
            params={
               'type': u'package',
               'slug': u'A New Title * With & Funny CHARacters',
            },
            status=200,
        )
        assert_equal(response.body, '{"valid": true}')
        assert_equal(response.header('Content-Type'), 'application/json;charset=utf-8')

        response = self.app.get(
            url=url_for(controller='api', action='is_slug_valid', ver=2),
            params={
               'type': u'package',
               'slug': u'warandpeace',
            },
            status=200,
        )
        assert_equal(response.body, '{"valid": false}')
        assert_equal(response.header('Content-Type'), 'application/json;charset=utf-8')

    def test_dataset_autocomplete_match_name(self):
        url = url_for(controller='api', action='dataset_autocomplete', ver=2)
        assert_equal(url, '/api/2/util/dataset/autocomplete')
        response = self.app.get(
            url=url,
            params={
               'incomplete': u'an',
            },
            status=200,
        )
        assert_equal(response.body, '{"ResultSet": {"Result": [{"match_field": "name", "match_displayed": "annakarenina", "name": "annakarenina", "title": "A Novel By Tolstoy"}]}}')
        assert_equal(response.header('Content-Type'), 'application/json;charset=utf-8')

    def test_dataset_autocomplete_match_title(self):
        url = url_for(controller='api', action='dataset_autocomplete', ver=2)
        assert_equal(url, '/api/2/util/dataset/autocomplete')
        response = self.app.get(
            url=url,
            params={
               'incomplete': u'a n',
            },
            status=200,
        )
        assert_equal(response.body, '{"ResultSet": {"Result": [{"match_field": "title", "match_displayed": "A Novel By Tolstoy (annakarenina)", "name": "annakarenina", "title": "A Novel By Tolstoy"}]}}')
        assert_equal(response.header('Content-Type'), 'application/json;charset=utf-8')

    def test_tag_autocomplete(self):
        url = url_for(controller='api', action='tag_autocomplete', ver=2)
        assert_equal(url, '/api/2/util/tag/autocomplete')
        response = self.app.get(
            url=url,
            params={
               'incomplete': u'ru',
            },
            status=200,
        )
        assert_equal(response.body, '{"ResultSet": {"Result": [{"Name": "russian"}]}}')
        assert_equal(response.header('Content-Type'), 'application/json;charset=utf-8')

    def test_group_autocomplete(self):
        url = url_for(controller='api', action='group_autocomplete', ver=2)
        assert_equal(url, '/api/2/util/group/autocomplete')
        response = self.app.get(
            url=url,
            params={
               'q': u'dave',
            },
            status=200,
        )
        results = json.loads(response.body)
        assert_equal(len(results), 1)
        assert_equal(results[0]['name'], 'david')
        assert_equal(results[0]['title'], 'Dave\'s books')
        assert_equal(response.header('Content-Type'), 'application/json;charset=utf-8')

    def test_markdown(self):
        markdown = '''##Title'''
        response = self.app.get(
            url=url_for(controller='api', action='markdown', ver=2),
            params={'q': markdown},
            status=200,
        )
        assert_equal(response.body, '"<h2>Title</h2>"')

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

    def test_status(self):
        response = self.app.get(
            url=url_for(controller='api', action='status', ver=2),
            params={},
            status=200,
        )
        res = json.loads(response.body)
        assert_equal(res['ckan_version'], __version__)
        assert_equal(res['site_url'], 'http://test.ckan.net')
        assert_equal(res['site_title'], 'CKAN')
        assert_equal(res['site_description'], '')
        assert_equal(res['locale_default'], 'en')

        assert_equal(type(res['extensions']), list)
        expected_extensions = set(('stats',))
        assert_equal(set(res['extensions']), expected_extensions)
