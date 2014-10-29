import mock
from nose import tools as nose_tools

from ckan.new_tests import helpers
from ckan.config import middleware


class TestCkanAuthTktMakeApp(object):

    '''Tests for middleware.ckan_auth_tkt_make_app method.'''

    @mock.patch('ckan.config.middleware.auth_tkt_make_plugin')
    def test_make_plugin_called_without_timeout_or_reissue_time(self, mock_auth_tkt_make_plugin):
        '''
        repoze.who.plugins.auth_tkt.make_plugin is called without timeout or
        reissue_time when these haven't been defined in the config or kwargs.
        '''
        # Make the call
        middleware.ckan_auth_tkt_make_app()

        # What was make_plugin called with?
        mock_call_args = mock_auth_tkt_make_plugin.call_args
        _, kwargs = mock_call_args

        nose_tools.assert_false('timeout' in kwargs.keys())
        nose_tools.assert_false('reissue_time' in kwargs.keys())

    @mock.patch('ckan.config.middleware.auth_tkt_make_plugin')
    def test_make_plugin_called_with_timeout_defined_as_kwargs(self, mock_auth_tkt_make_plugin):
        '''
        kwargs are passed into ckan_auth_tkt_make_app come from who.ini and
        should be passed to make_plugin.
        '''
        middleware.ckan_auth_tkt_make_app(timeout=2000)

        mock_call_args = mock_auth_tkt_make_plugin.call_args
        _, kwargs = mock_call_args

        nose_tools.assert_true(('timeout', 2000) in kwargs.items())
        nose_tools.assert_true(('reissue_time', 200) in kwargs.items())

    @mock.patch('ckan.config.middleware.auth_tkt_make_plugin')
    def test_make_plugin_called_with_timeout_and_reissue_time_defined_in_kwargs(self, mock_auth_tkt_make_plugin):
        '''
        kwargs are passed into ckan_auth_tkt_make_app come from who.ini and
        should be passed to make_plugin.
        '''
        middleware.ckan_auth_tkt_make_app(timeout=2000, reissue_time=100)

        mock_call_args = mock_auth_tkt_make_plugin.call_args
        _, kwargs = mock_call_args

        nose_tools.assert_true(('timeout', 2000) in kwargs.items())
        nose_tools.assert_true(('reissue_time', 100) in kwargs.items())

    @mock.patch('ckan.config.middleware.auth_tkt_make_plugin')
    @helpers.change_config('who.timeout', 9000)
    def test_make_plugin_called_with_timeout_from_config(self, mock_auth_tkt_make_plugin):
        '''
        repoze.who.plugins.auth_tkt.make_plugin is called with timeout defined
        in config, but no reissue_time (one will be created).
        '''
        middleware.ckan_auth_tkt_make_app()

        mock_call_args = mock_auth_tkt_make_plugin.call_args
        _, kwargs = mock_call_args

        nose_tools.assert_true(('timeout', 9000) in kwargs.items())
        nose_tools.assert_true(('reissue_time', 900) in kwargs.items())

    @mock.patch('ckan.config.middleware.auth_tkt_make_plugin')
    @helpers.change_config('who.timeout', 9000)
    @helpers.change_config('who.reissue_time', 200)
    def test_make_plugin_called_with_reissue_from_config(self, mock_auth_tkt_make_plugin):
        '''
        repoze.who.plugins.auth_tkt.make_plugin is called with timeout and
        reissue_time defined in config.
        '''
        middleware.ckan_auth_tkt_make_app()

        mock_call_args = mock_auth_tkt_make_plugin.call_args
        _, kwargs = mock_call_args

        nose_tools.assert_true(('timeout', 9000) in kwargs.items())
        nose_tools.assert_true(('reissue_time', 200) in kwargs.items())

    @mock.patch('ckan.config.middleware.auth_tkt_make_plugin')
    @helpers.change_config('who.timeout', 9000)
    @helpers.change_config('who.reissue_time', 200)
    def test_make_plugin_called_with_kwargs_supersede_config(self, mock_auth_tkt_make_plugin):
        '''
        keyword args (who.ini values) supersede those in config.
        '''
        middleware.ckan_auth_tkt_make_app(timeout=8000, reissue_time=500)

        mock_call_args = mock_auth_tkt_make_plugin.call_args
        _, kwargs = mock_call_args

        nose_tools.assert_true(('timeout', 8000) in kwargs.items())
        nose_tools.assert_true(('reissue_time', 500) in kwargs.items())
