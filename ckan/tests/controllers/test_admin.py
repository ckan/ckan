from nose import tools as nosetools

from routes import url_for
from pylons import config

import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan.model.system_info import get_system_info

webtest_submit = helpers.webtest_submit


class TestAdminConfigUpdate(helpers.FunctionalTestBase):

    def teardown(self):
        '''Reset the database and clear the search indexes.'''
        helpers.reset_db()

    def _update_config_option(self):
        sysadmin = factories.Sysadmin()
        env = {'REMOTE_USER': sysadmin['name'].encode('ascii')}
        app = self._get_test_app()
        url = url_for(controller='admin', action='config')

        response = app.get(url=url, extra_environ=env)
        form = response.forms[1]
        form['ckan.site_title'] = 'My Updated Site Title'

        webtest_submit(form, 'save', status=302, extra_environ=env)

    def test_admin_config_update(self):
        '''Changing a config option using the admin interface appropriately
        updates value returned by config_option_show,
        system_info.get_system_info and in the title tag in templates.'''

        # test value before update
        # config_option_show returns default value
        before_update = helpers.call_action('config_option_show',
                                            key='ckan.site_title')
        nosetools.assert_equal(before_update, 'CKAN')

        # system_info.get_system_info returns None, or default
        # test value before update
        before_update = get_system_info('ckan.site_title')
        nosetools.assert_equal(before_update, None)
        # test value before update with default
        before_update_default = get_system_info('ckan.site_title',
                                                config['ckan.site_title'])
        nosetools.assert_equal(before_update_default, 'CKAN')

        # title tag contains default value
        app = self._get_test_app()
        home_page_before = app.get('/', status=200)
        nosetools.assert_true('Welcome - CKAN' in home_page_before)

        # update the option
        self._update_config_option()

        # test config_option_show returns new value after update
        after_update = helpers.call_action('config_option_show',
                                           key='ckan.site_title')
        nosetools.assert_equal(after_update, 'My Updated Site Title')

        # system_info.get_system_info returns new value
        after_update = get_system_info('ckan.site_title')
        nosetools.assert_equal(after_update, 'My Updated Site Title')
        # test value after update with default
        after_update_default = get_system_info('ckan.site_title',
                                               config['ckan.site_title'])
        nosetools.assert_equal(after_update_default, 'My Updated Site Title')

        # title tag contains new value
        home_page_after = app.get('/', status=200)
        nosetools.assert_true('Welcome - My Updated Site Title'
                              in home_page_after)
