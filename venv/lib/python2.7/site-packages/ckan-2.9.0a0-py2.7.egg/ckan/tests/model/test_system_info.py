# encoding: utf-8

import nose.tools

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories

from ckan import model
from ckan.model.system_info import (SystemInfo,
                                    get_system_info,
                                    set_system_info,
                                    delete_system_info,
                                    system_info_revision_table,
                                    )


assert_equals = nose.tools.assert_equals
assert_not_equals = nose.tools.assert_not_equals


class TestSystemInfo(object):

    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    @classmethod
    def teardown_class(cls):
        helpers.reset_db()

    def test_set_value(self):

        key = 'config_option_1'
        value = 'test_value'

        set_system_info(key, value)

        results = model.Session.query(SystemInfo).filter_by(key=key).all()

        assert_equals(len(results), 1)

        obj = results[0]

        assert_equals(obj.key, key)
        assert_equals(obj.value, value)

    def test_sets_new_value_for_same_key(self):

        config = factories.SystemInfo()
        first_revision = config.revision_id

        set_system_info(config.key, 'new_value')

        new_config = model.Session.query(SystemInfo) \
                                  .filter_by(key=config.key).first()

        assert_equals(config.id, new_config.id)
        assert_not_equals(first_revision, new_config.revision_id)

        assert_equals(new_config.value, 'new_value')

    def test_does_not_set_same_value_for_same_key(self):

        config = factories.SystemInfo()

        set_system_info(config.key, config.value)

        new_config = model.Session.query(SystemInfo) \
                                  .filter_by(key=config.key).first()

        assert_equals(config.id, new_config.id)
        assert_equals(config.revision_id, new_config.revision_id)
