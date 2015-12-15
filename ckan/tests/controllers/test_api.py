'''
NB Don't test logic functions here. This is just for the mechanics of the API
controller itself.
'''
import json

from routes import url_for
from nose.tools import assert_equal

import ckan.tests.helpers as helpers
from ckan.tests import factories


class TestApiController(helpers.FunctionalTestBase):

    def test_unicode_in_error_message_works_ok(self):
        # Use tag_delete to echo back some unicode
        app = self._get_test_app()
        org_url = '/api/action/tag_delete'
        data_dict = {'id': u'Delta symbol: \u0394'}  # unicode gets rec'd ok
        postparams = '%s=1' % json.dumps(data_dict)
        response = app.post(url=org_url, params=postparams, status=404)
        # The unicode is backslash encoded (because that is the default when
        # you do str(exception) )
        assert 'Delta symbol: \\u0394' in response.body

    def test_dataset_autocomplete_name(self):
        dataset = factories.Dataset(name='rivers')
        url = url_for(controller='api', action='dataset_autocomplete', ver='/2')
        assert_equal(url, '/api/2/util/dataset/autocomplete')
        app = self._get_test_app()

        response = app.get(
            url=url,
            params={
                'incomplete': u'rive',
            },
            status=200,
        )

        results = json.loads(response.body)
        assert_equal(results, {"ResultSet": {"Result": [{
            'match_field': 'name',
            "name": "rivers",
            'match_displayed': 'rivers',
            'title': dataset['title'],
        }]}})
        assert_equal(response.headers['Content-Type'],
                     'application/json;charset=utf-8')

    def test_dataset_autocomplete_title(self):
        dataset = factories.Dataset(name='test_ri', title='Rivers')
        url = url_for(controller='api', action='dataset_autocomplete', ver='/2')
        assert_equal(url, '/api/2/util/dataset/autocomplete')
        app = self._get_test_app()

        response = app.get(
            url=url,
            params={
                'incomplete': u'riv',
            },
            status=200,
        )

        results = json.loads(response.body)
        assert_equal(results, {"ResultSet": {"Result": [{
            'match_field': 'title',
            "name": dataset['name'],
            'match_displayed': 'Rivers (test_ri)',
            'title': 'Rivers',
        }]}})
        assert_equal(response.headers['Content-Type'],
                     'application/json;charset=utf-8')

    def test_tag_autocomplete(self):
        factories.Dataset(tags=[{'name': 'rivers'}])
        url = url_for(controller='api', action='tag_autocomplete', ver='/2')
        assert_equal(url, '/api/2/util/tag/autocomplete')
        app = self._get_test_app()

        response = app.get(
            url=url,
            params={
                'incomplete': u'rive',
            },
            status=200,
        )

        results = json.loads(response.body)
        assert_equal(results, {"ResultSet": {"Result": [{"Name": "rivers"}]}})
        assert_equal(response.headers['Content-Type'],
                     'application/json;charset=utf-8')

    def test_group_autocomplete_by_name(self):
        org = factories.Group(name='rivers', title='Bridges')
        url = url_for(controller='api', action='group_autocomplete', ver='/2')
        assert_equal(url, '/api/2/util/group/autocomplete')
        app = self._get_test_app()

        response = app.get(
            url=url,
            params={
                'q': u'rive',
            },
            status=200,
        )

        results = json.loads(response.body)
        assert_equal(len(results), 1)
        assert_equal(results[0]['name'], 'rivers')
        assert_equal(results[0]['title'], 'Bridges')
        assert_equal(response.headers['Content-Type'],
                     'application/json;charset=utf-8')

    def test_group_autocomplete_by_title(self):
        org = factories.Group(name='frogs', title='Bugs')
        url = url_for(controller='api', action='group_autocomplete', ver='/2')
        app = self._get_test_app()

        response = app.get(
            url=url,
            params={
                'q': u'bug',
            },
            status=200,
        )

        results = json.loads(response.body)
        assert_equal(len(results), 1)
        assert_equal(results[0]['name'], 'frogs')

    def test_organization_autocomplete_by_name(self):
        org = factories.Organization(name='simple-dummy-org')
        url = url_for(controller='api', action='organization_autocomplete', ver='/2')
        assert_equal(url, '/api/2/util/organization/autocomplete')
        app = self._get_test_app()

        response = app.get(
            url=url,
            params={
                'q': u'simple',
            },
            status=200,
        )

        results = json.loads(response.body)
        assert_equal(len(results), 1)
        assert_equal(results[0]['name'], 'simple-dummy-org')
        assert_equal(results[0]['title'], org['title'])
        assert_equal(response.headers['Content-Type'],
                     'application/json;charset=utf-8')

    def test_organization_autocomplete_by_title(self):
        org = factories.Organization(title='Simple dummy org')
        url = url_for(controller='api', action='organization_autocomplete', ver='/2')
        app = self._get_test_app()

        response = app.get(
            url=url,
            params={
                'q': u'simple dum',
            },
            status=200,
        )

        results = json.loads(response.body)
        assert_equal(len(results), 1)
        assert_equal(results[0]['title'], 'Simple dummy org')

    def test_config_option_list_access_sysadmin(self):
        user = factories.Sysadmin()
        url = url_for(
            controller='api',
            action='action',
            logic_function='config_option_list',
            ver='/3')
        app = self._get_test_app()

        app.get(
            url=url,
            params={},
            extra_environ={'REMOTE_USER': user['name'].encode('ascii')},
            status=200,
        )

    def test_config_option_list_access_sysadmin_jsonp(self):
        user = factories.Sysadmin()
        url = url_for(
            controller='api',
            action='action',
            logic_function='config_option_list',
            ver='/3')
        app = self._get_test_app()

        app.get(
            url=url,
            params={'callback': 'myfn'},
            extra_environ={'REMOTE_USER': user['name'].encode('ascii')},
            status=403,
        )
