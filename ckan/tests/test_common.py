# encoding: utf-8

import flask
import pylons

from nose.tools import eq_, assert_not_equal as neq_, assert_raises

from ckan.tests import helpers
from ckan.common import (CKANConfig, config as ckan_config,
                         request as ckan_request, g as ckan_g, c as ckan_c)


class TestConfigObject(object):

    def test_del_works(self):
        my_conf = CKANConfig()

        my_conf[u'test_key_1'] = u'Test value 1'

        del my_conf[u'test_key_1']

        assert u'test_key_1' not in my_conf

    def test_get_item_works(self):
        my_conf = CKANConfig()

        my_conf[u'test_key_1'] = u'Test value 1'

        eq_(my_conf.get(u'test_key_1'), u'Test value 1')

    def test_repr_works(self):
        my_conf = CKANConfig()

        my_conf[u'test_key_1'] = u'Test value 1'

        eq_(repr(my_conf), u"{u'test_key_1': u'Test value 1'}")

    def test_len_works(self):

        my_conf = CKANConfig()

        my_conf[u'test_key_1'] = u'Test value 1'
        my_conf[u'test_key_2'] = u'Test value 2'

        eq_(len(my_conf), 2)

    def test_keys_works(self):

        my_conf = CKANConfig()

        my_conf[u'test_key_1'] = u'Test value 1'
        my_conf[u'test_key_2'] = u'Test value 2'

        eq_(sorted(my_conf.keys()), [u'test_key_1', u'test_key_2'])

    def test_clear_works(self):

        # Keep a copy of the original Pylons config
        _original_pylons_config = pylons.config.copy()

        my_conf = CKANConfig()

        my_conf[u'test_key_1'] = u'Test value 1'
        my_conf[u'test_key_2'] = u'Test value 2'

        eq_(len(my_conf.keys()), 2)

        my_conf.clear()

        eq_(len(my_conf.keys()), 0)

        # Restore Pylons config
        pylons.config.update(_original_pylons_config)

    def test_for_in_works(self):

        my_conf = CKANConfig()

        my_conf[u'test_key_1'] = u'Test value 1'
        my_conf[u'test_key_2'] = u'Test value 2'

        cnt = 0
        for key in my_conf:
            cnt += 1
            assert key.startswith(u'test_key_')

        eq_(cnt, 2)

    def test_iteritems_works(self):

        my_conf = CKANConfig()

        my_conf[u'test_key_1'] = u'Test value 1'
        my_conf[u'test_key_2'] = u'Test value 2'

        cnt = 0
        for key, value in my_conf.iteritems():
            cnt += 1
            assert key.startswith(u'test_key_')
            assert value.startswith(u'Test value')

        eq_(cnt, 2)

    def test_not_true_if_empty(self):

        my_conf = CKANConfig()

        assert not my_conf

    def test_true_if_not_empty(self):

        my_conf = CKANConfig()

        my_conf[u'test_key_1'] = u'Test value 1'

        assert my_conf


class TestCommonConfig(object):

    def setup(self):
        self._original_config = ckan_config.copy()

    def teardown(self):
        ckan_config.clear()
        ckan_config.update(self._original_config)

    @classmethod
    def teardown_class(cls):
        helpers.reset_db()

    def test_setting_a_key_sets_it_on_pylons_config(self):

        ckan_config[u'ckan.site_title'] = u'Example title'
        eq_(pylons.config[u'ckan.site_title'], u'Example title')

    def test_setting_a_key_sets_it_on_flask_config_if_app_context(self):

        app = helpers._get_test_app()
        with app.flask_app.app_context():

            ckan_config[u'ckan.site_title'] = u'Example title'
            eq_(flask.current_app.config[u'ckan.site_title'], u'Example title')

    def test_setting_a_key_does_not_set_it_on_flask_config_if_outside_app_context(self):

        ckan_config[u'ckan.site_title'] = u'Example title'

        app = helpers._get_test_app()
        with app.flask_app.app_context():

            neq_(flask.current_app.config[u'ckan.site_title'], u'Example title')

    def test_deleting_a_key_deletes_it_on_pylons_config(self):

        ckan_config[u'ckan.site_title'] = u'Example title'
        del ckan_config[u'ckan.site_title']

        assert u'ckan.site_title' not in ckan_config

    def test_deleting_a_key_delets_it_on_flask_config(self):

        app = helpers._get_test_app()
        with app.flask_app.app_context():

            ckan_config[u'ckan.site_title'] = u'Example title'
            del ckan_config[u'ckan.site_title']

            assert u'ckan.site_title' not in flask.current_app.config

    def test_update_works_on_pylons_config(self):

        ckan_config[u'ckan.site_title'] = u'Example title'

        ckan_config.update({
            u'ckan.site_title': u'Example title 2',
            u'ckan.new_key': u'test'})

        eq_(pylons.config[u'ckan.site_title'], u'Example title 2')
        eq_(pylons.config[u'ckan.new_key'], u'test')

    def test_update_works_on_flask_config(self):

        app = helpers._get_test_app()
        with app.flask_app.app_context():

            ckan_config[u'ckan.site_title'] = u'Example title'

            ckan_config.update({
                u'ckan.site_title': u'Example title 2',
                u'ckan.new_key': u'test'})

            eq_(flask.current_app.config[u'ckan.site_title'], u'Example title 2')
            eq_(flask.current_app.config[u'ckan.new_key'], u'test')

    def test_config_option_update_action_works_on_pylons(self):
        params = {
            u'ckan.site_title': u'Example title action',
        }

        helpers.call_action(u'config_option_update', {}, **params)

        eq_(pylons.config[u'ckan.site_title'], u'Example title action')

    def test_config_option_update_action_works_on_flask(self):
        app = helpers._get_test_app()
        with app.flask_app.app_context():

            params = {
                u'ckan.site_title': u'Example title action',
            }

            helpers.call_action(u'config_option_update', {}, **params)

            eq_(pylons.config[u'ckan.site_title'], u'Example title action')


class TestCommonRequest(object):

    def test_params_also_works_on_flask_request(self):

        app = helpers._get_test_app()

        with app.flask_app.test_request_context(u'/hello?a=1'):

            assert u'a' in ckan_request.args
            assert u'a' in ckan_request.params

    def test_other_missing_attributes_raise_attributeerror_exceptions(self):

        app = helpers._get_test_app()

        with app.flask_app.test_request_context(u'/hello?a=1'):

            assert_raises(AttributeError, getattr, ckan_request, u'not_here')


class TestCommonG(object):

    def test_flask_g_is_used_on_a_flask_request(self):

        app = helpers._get_test_app()

        with app.flask_app.test_request_context():

            assert u'flask.g' in unicode(ckan_g)

            flask.g.user = u'example'

            eq_(ckan_g.user, u'example')

    def test_can_also_use_c_on_a_flask_request(self):

        app = helpers._get_test_app()

        with app.flask_app.test_request_context():

            flask.g.user = u'example'

            eq_(ckan_c.user, u'example')

            ckan_g.user = u'example2'

            eq_(ckan_c.user, u'example2')

    def test_accessing_missing_key_raises_error_on_flask_request(self):

        app = helpers._get_test_app()

        with app.flask_app.test_request_context():

            assert_raises(AttributeError, getattr, ckan_g, u'user')
