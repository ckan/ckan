# encoding: utf-8

import pytest

import ckan.tests.factories as factories
from ckan import model
from ckan.model.system_info import SystemInfo, set_system_info


@pytest.mark.usefixtures("non_clean_db")
class TestSystemInfo(object):
    def test_set_value(self):

        key = factories.SystemInfo.stub().key
        value = "test_value"
        set_system_info(key, value)

        results = model.Session.query(SystemInfo).filter_by(key=key).all()

        assert len(results) == 1

        obj = results[0]

        assert obj.key == key
        assert obj.value == value

    def test_sets_new_value_for_same_key(self):

        config = factories.SystemInfo()
        config = factories.SystemInfo()

        new_config = (
            model.Session.query(SystemInfo).filter_by(key=config.key).first()
        )

        assert config.id == new_config.id

        assert config.id == new_config.id

    def test_does_not_set_same_value_for_same_key(self):

        config = factories.SystemInfo()

        set_system_info(config.key, config.value)

        new_config = (
            model.Session.query(SystemInfo).filter_by(key=config.key).first()
        )

        assert config.id == new_config.id
