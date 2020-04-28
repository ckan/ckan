# -*- coding: utf-8 -*-

import pytest
import ckan.plugins.toolkit as tk
import ckan.plugins as p

before_action = tk.signals.before_action
isignal_number = tk.signals.ckanext.signal(u'isignal_number')


def test_default_listeners():
    """No listeners are registered without enabled plugin.
    """
    assert len(before_action.receivers) == 0
    assert list(isignal_number.receivers_for(10)) == []


def test_signals_setup_teardown():
    """Plugin connects listeners when loaded and disconnects, when
    unloaded.

    """
    assert len(before_action.receivers) == 0
    assert list(isignal_number.receivers_for(10)) == []
    with p.use_plugin(u'example_isignal'):
        assert len(before_action.receivers) == 1
        assert len(list(isignal_number.receivers_for(10))) == 2
    assert len(before_action.receivers) == 0
    assert list(isignal_number.receivers_for(10)) == []


@pytest.mark.ckan_config(u'ckan.plugins', u'example_isignal')
@pytest.mark.usefixtures(u'with_plugins')
class TestISignalPlugin(object):
    def test_plugin_listeners(self):
        """Enabled plugin connects its listeners.
        """
        assert len(before_action.receivers) == 1
        assert len(isignal_number.receivers) == 2

    def test_action_logger(self):
        """Listener can be a callable class.
        """
        log = tk.h.isignal_action_logger
        log.reset()
        assert log.actions == []
        tk.get_action(u'package_search')(None, {u'q': u'*:*'})
        assert log.actions == [u'package_search']
        tk.get_action(u'status_show')(None, {})
        assert log.actions == [u'package_search', u'status_show']

    def test_return_value(self):
        """Return values can be collected.
        """
        result = isignal_number.send(5)
        assert [r[1] for r in result] == [10]

        result = isignal_number.send(10)
        assert sorted([r[1] for r in result]) == [20, 100]
