# encoding: utf-8

import nose.tools

from ckan.common import config

import ckan.lib.app_globals as app_globals

import ckan.model as model
import ckan.logic as logic
import ckan.plugins as plugins
import ckan.tests.helpers as helpers


assert_equals = nose.tools.assert_equals


class TestConfigOptionUpdatePluginNotEnabled(object):

    def test_updating_unregistered_core_setting_not_allowed(self):
        key = 'ckan.datasets_per_page'
        value = 5

        params = {key: value}

        nose.tools.assert_raises(logic.ValidationError, helpers.call_action,
                                 'config_option_update',
                                 **params)

    def test_updating_unregistered_new_setting_not_allowed(self):
        key = 'ckanext.example_iconfigurer.test_conf'
        value = 'Test value'

        params = {key: value}

        nose.tools.assert_raises(logic.ValidationError, helpers.call_action,
                                 'config_option_update',
                                 **params)


class TestConfigOptionUpdatePluginEnabled(object):

    @classmethod
    def setup_class(cls):
        if not plugins.plugin_loaded('example_iconfigurer'):
            plugins.load('example_iconfigurer')

        cls._datasets_per_page_original_value = \
            config.get('ckan.datasets_per_page')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_iconfigurer')
        config['ckan.datasets_per_page'] = \
            cls._datasets_per_page_original_value
        helpers.reset_db()

    def setup(self):
        helpers.reset_db()

    def test_update_registered_core_value(self):

        key = 'ckan.datasets_per_page'
        value = 5

        params = {key: value}

        assert_equals(config[key], self._datasets_per_page_original_value)

        new_config = helpers.call_action('config_option_update', **params)

        # output
        assert_equals(new_config[key], value)

        # config
        assert_equals(config[key], value)

        # app_globals
        globals_key = app_globals.get_globals_key(key)
        assert hasattr(app_globals.app_globals, globals_key)

        # db
        obj = model.Session.query(model.SystemInfo).filter_by(key=key).first()
        assert_equals(obj.value, unicode(value))  # all values stored as string

    def test_update_registered_external_value(self):

        key = 'ckanext.example_iconfigurer.test_conf'
        value = 'Test value'

        params = {key: value}

        assert key not in config

        new_config = helpers.call_action('config_option_update', **params)

        # output
        assert_equals(new_config[key], value)

        # config
        assert_equals(config[key], value)

        # db
        obj = model.Session.query(model.SystemInfo).filter_by(key=key).first()
        assert_equals(obj.value, value)

        # not set in globals
        globals_key = app_globals.get_globals_key(key)
        assert not hasattr(app_globals.app_globals, globals_key)

    def test_update_registered_core_value_in_list(self):
        '''Registering a core key/value will allow it to be included in the
        list returned by config_option_list action.'''

        key = 'ckan.datasets_per_page'
        value = 5
        params = {key: value}

        # add registered core value
        helpers.call_action('config_option_update', **params)

        option_list = helpers.call_action('config_option_list')

        assert key in option_list

    def test_update_registered_core_value_in_show(self):
        '''Registering a core key/value will allow it to be shown by the
        config_option_show action.'''

        key = 'ckan.datasets_per_page'
        value = 5
        params = {key: value}

        # add registered core value
        helpers.call_action('config_option_update', **params)

        show_value = helpers.call_action('config_option_show',
                                         key='ckan.datasets_per_page')

        assert show_value == value

    def test_update_registered_external_value_in_list(self):
        '''Registering an external key/value will allow it to be included in
        the list returned by config_option_list action.'''

        key = 'ckanext.example_iconfigurer.test_conf'
        value = 'Test value'
        params = {key: value}

        # add registered external value
        helpers.call_action('config_option_update', **params)

        option_list = helpers.call_action('config_option_list')

        assert key in option_list

    def test_update_registered_external_value_in_show(self):
        '''Registering an external key/value will allow it to be shown by the
        config_option_show action.'''

        key = 'ckanext.example_iconfigurer.test_conf'
        value = 'Test value'
        params = {key: value}

        # add registered external value
        helpers.call_action('config_option_update', **params)

        show_value = helpers.call_action(
            'config_option_show',
            key='ckanext.example_iconfigurer.test_conf')

        assert show_value == value
