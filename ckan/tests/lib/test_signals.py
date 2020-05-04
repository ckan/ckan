# -*- coding: utf-8 -*-

import mock

import pytest
import ckan.plugins.toolkit as tk
import ckan.tests.helpers as h


@pytest.mark.parametrize(u'action,args', [
    (u'status_show', {}),
    (u'package_search', {u'q': u'title:title'})
])
def test_before_action(action, args):
    receiver = mock.Mock()
    with tk.signals.before_action.connected_to(receiver):
        h.call_action(action, **args)
    receiver.assert_called_once()

    (name, ), kwargs = receiver.call_args

    assert name == action
    assert kwargs[u'data_dict'] == args


def test_after_action():
    receiver = mock.Mock()
    with tk.signals.after_action.connected_to(receiver):
        h.call_action(u'status_show')
    receiver.assert_called_once()
    (name, ), kwargs = receiver.call_args
    assert name == u'status_show'
    assert kwargs[u'result'][u'ckan_version'] == tk.h.ckan_version()


@pytest.mark.ckan_config(u"ckan.plugins", u"example_idatasetform_v6")
def test_register_blueprint(make_app):
    receiver = mock.Mock()
    with tk.signals.register_blueprint.connected_to(receiver):
        make_app()
    assert receiver.call_count == 2
    (type_, ), _ = receiver.call_args_list[0]
    assert type_ == u'dataset'

    (type_, ), _ = receiver.call_args_list[1]
    assert type_ == u'resource'
