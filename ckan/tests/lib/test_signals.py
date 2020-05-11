# -*- coding: utf-8 -*-

import mock

import pytest
import ckan.plugins.toolkit as tk


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


def test_request_signals(app):
    start_receiver = mock.Mock()
    finish_receiver = mock.Mock()
    with tk.signals.request_started.connected_to(start_receiver):
        with tk.signals.request_finished.connected_to(finish_receiver):
            app.get(u'/')
    assert start_receiver.call_count == 1
    assert finish_receiver.call_count == 1

    with tk.signals.request_started.connected_to(start_receiver):
        with tk.signals.request_finished.connected_to(finish_receiver):
            app.get(u'/about')
    assert start_receiver.call_count == 2
    assert finish_receiver.call_count == 2
