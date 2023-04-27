# -*- coding: utf-8 -*-

import pytest
import ckan.plugins.toolkit as tk
import ckan.plugins as p

isignal_number = tk.signals.ckanext.signal(u'isignal_number')


def test_default_listeners():
    """No listeners are registered without enabled plugin.
    """
    assert list(isignal_number.receivers_for(10)) == []


def test_signals_setup_teardown():
    """Plugin connects listeners when loaded and disconnects, when
    unloaded.

    """
    assert list(isignal_number.receivers_for(10)) == []
    with p.use_plugin(u'example_isignal'):
        assert len(list(isignal_number.receivers_for(10))) == 2
    assert list(isignal_number.receivers_for(10)) == []


@pytest.mark.ckan_config(u'ckan.plugins', u'example_isignal')
@pytest.mark.usefixtures(u'with_plugins')
class TestISignalPlugin(object):
    def test_plugin_listeners(self):
        """Enabled plugin connects its listeners.
        """
        assert len(isignal_number.receivers) == 2

    def test_return_value(self):
        """Return values can be collected.
        """
        result = isignal_number.send(5)
        assert [r[1] for r in result] == [10]

        result = isignal_number.send(10)
        assert sorted([r[1] for r in result]) == [20, 100]
