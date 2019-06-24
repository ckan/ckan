
#encoding: utf-8
from nose.tools import assert_true, assert_equal
from ckan.lib.helpers import url_for
from ckan.common import config
import ckan.model as model
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
from ckan.model.system_info import get_system_info

webtest_submit = helpers.webtest_submit

class TestTrashPView(helpers.FunctionalTestBase):

    def test_trash_purge_one_deleted_dataset(self):
      '''Posting the trash view with 'deleted' dataset, purges the
        dataset.'''
      user = factories.Sysadmin()
      dataset = factories.Dataset(state='deleted')
      resource = factories.Resource(package_id=dataset['id'],
                                    format='csv',
                                    url="http://example.com/x.csv")
      app = self._get_test_app()
      resource_before_purge = model.Session.query(model.Resource).count()
      assert_equal(resource_before_purge, 1)
      env = {'REMOTE_USER': user['name'].encode('ascii')}
      trash_url = url_for(controller='admin', action='trash')
      trash_response = app.get(trash_url, extra_environ=env, status=200)
      purge_form = trash_response.forms['form-purge-packages']
      purge_response = webtest_submit(purge_form, 'purge-packages',
                                      status=302, extra_environ=env)
      purge_response = purge_response.follow(extra_environ=env)
      assert_true('Purge complete' in purge_response)
      resource_after_purge = model.Session.query(model.Resource).count()
      assert_equal(resource_after_purge, 0)

    def test_trash_purge_delete_two_datasets(self):
      user = factories.Sysadmin()
      dataset = factories.Dataset(state='deleted')
      resource1  = factories.Resource(package_id=dataset['id'],
                                      format='csv',
                                      url="http://example.com/x.csv")
      resource2  = factories.Resource(package_id=dataset['id'],
                                      format='csv',
                                      url="http://example.com/x.csv")
      app = self._get_test_app()
      resource_before_purge = model.Session.query(model.Resource).count()
      assert_equal(resource_before_purge, 2)
      env = {'REMOTE_USER': user['name'].encode('ascii')}
      trash_url = url_for(controller='admin', action='trash')
      trash_response = app.get(trash_url, extra_environ=env, status=200)
      purge_form = trash_response.forms['form-purge-packages']
      purge_response = webtest_submit(purge_form, 'purge-packages',
                                      status=302, extra_environ=env)
      purge_response = purge_response.follow(extra_environ=env)
      assert_true('Purge complete' in purge_response)
      resource_after_purge = model.Session.query(model.Resource).count()
      assert_equal(resource_after_purge, 0)
