# encoding: utf-8

import flask
import pytest

from ckan.common import (
    CKANConfig,
    config as ckan_config,
    request as ckan_request,
    g as ckan_g,
    c as ckan_c,
)
from ckan.tests import helpers


def test_del_works():
    my_conf = CKANConfig()
    my_conf[u"test_key_1"] = u"Test value 1"
    del my_conf[u"test_key_1"]
    assert u"test_key_1" not in my_conf


def test_get_item_works():
    my_conf = CKANConfig()
    my_conf[u"test_key_1"] = u"Test value 1"
    assert my_conf.get(u"test_key_1") == u"Test value 1"


def test_repr_works():
    my_conf = CKANConfig()
    my_conf[u"test_key_1"] = u"Test value 1"
    assert repr(my_conf) == u"{'test_key_1': 'Test value 1'}"


def test_len_works():
    my_conf = CKANConfig()
    my_conf[u"test_key_1"] = u"Test value 1"
    my_conf[u"test_key_2"] = u"Test value 2"
    assert len(my_conf) == 2


def test_keys_works():
    my_conf = CKANConfig()
    my_conf[u"test_key_1"] = u"Test value 1"
    my_conf[u"test_key_2"] = u"Test value 2"
    assert sorted(my_conf.keys()) == [u"test_key_1", u"test_key_2"]


def test_clear_works():
    my_conf = CKANConfig()
    my_conf[u"test_key_1"] = u"Test value 1"
    my_conf[u"test_key_2"] = u"Test value 2"
    assert len(my_conf.keys()) == 2

    my_conf.clear()
    assert len(my_conf.keys()) == 0


def test_for_in_works():
    my_conf = CKANConfig()
    my_conf[u"test_key_1"] = u"Test value 1"
    my_conf[u"test_key_2"] = u"Test value 2"
    cnt = 0
    for key in my_conf:
        cnt += 1
        assert key.startswith(u"test_key_")
    assert cnt == 2


def test_iteritems_works():
    my_conf = CKANConfig()
    my_conf[u"test_key_1"] = u"Test value 1"
    my_conf[u"test_key_2"] = u"Test value 2"

    cnt = 0
    for key, value in my_conf.items():
        cnt += 1
        assert key.startswith(u"test_key_")
        assert value.startswith(u"Test value")

    assert cnt == 2


def test_not_true_if_empty():
    my_conf = CKANConfig()
    assert not my_conf


def test_true_if_not_empty():
    my_conf = CKANConfig()
    my_conf[u"test_key_1"] = u"Test value 1"
    assert my_conf


@pytest.mark.usefixtures("with_request_context")
def test_setting_a_key_sets_it_on_flask_config_if_app_context(monkeypatch):
    monkeypatch.setitem(ckan_config, u"ckan.site_title", u"Example title")
    assert flask.current_app.config[u"ckan.site_title"] == u"Example title"


@pytest.mark.usefixtures("with_request_context")
@pytest.mark.ckan_config("ckan.site_title", "Example title")
@pytest.mark.flaky(retries=3, delay=1)
def test_setting_a_key_does_set_it_on_flask_config_if_outside_app_context():
    assert flask.current_app.config["ckan.site_title"] == "Example title"


@pytest.mark.ckan_config(u"ckan.site_title", u"Example title")
def test_deleting_a_key_deletes_it_on_ckan_config():
    del ckan_config[u"ckan.site_title"]
    assert u"ckan.site_title" not in ckan_config


# START-CONFIG-OVERRIDE
@pytest.mark.usefixtures("with_request_context")
def test_deleting_a_key_delets_it_on_flask_config(monkeypatch, ckan_config):
    monkeypatch.setitem(ckan_config, u"ckan.site_title", u"Example title")
    del ckan_config[u"ckan.site_title"]
    assert u"ckan.site_title" not in flask.current_app.config


# END-CONFIG-OVERRIDE


@pytest.mark.usefixtures("with_request_context")
def test_update_works_on_flask_config():
    ckan_config[u"ckan.site_title"] = u"Example title"

    ckan_config.update(
        {u"ckan.site_title": u"Example title 2", u"ckan.new_key": u"test"}
    )
    assert flask.current_app.config[u"ckan.site_title"] == u"Example title 2"
    assert flask.current_app.config[u"ckan.new_key"] == u"test"


def test_config_option_update_action_works_on_flask(reset_db, ckan_config):
    params = {u"ckan.site_title": u"Example title action"}
    helpers.call_action(u"config_option_update", {}, **params)
    assert ckan_config[u"ckan.site_title"] == u"Example title action"
    reset_db()


def test_params_also_works_on_flask_request(test_request_context):
    with test_request_context(u"/?a=1"):
        assert u"a" in ckan_request.args
        assert u"a" in ckan_request.args


def test_other_missing_attributes_raise_attributeerror_exceptions(
    test_request_context,
):
    with test_request_context(u"/?a=1"):
        with pytest.raises(AttributeError):
            getattr(ckan_request, u"not_here")


@pytest.mark.usefixtures("with_request_context")
def test_flask_g_is_used_on_a_flask_request():
    assert u"flask.g" in str(ckan_g)
    flask.g.user = u"example"
    assert ckan_g.user == u"example"


@pytest.mark.usefixtures("with_request_context")
def test_can_also_use_c_on_a_flask_request():
    flask.g.user = u"example"
    assert ckan_c.user == u"example"

    ckan_g.user = u"example2"
    assert ckan_c.user == u"example2"


@pytest.mark.usefixtures("with_request_context")
def test_accessing_missing_key_raises_error_on_flask_request():
    with pytest.raises(AttributeError):
        getattr(ckan_g, u"user")
