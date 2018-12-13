# encoding: utf-8

from ckan.tests.helpers import _get_test_app
from ckan.common import config


class StatsFixture(object):

    @classmethod
    def setup_class(cls):
        cls._original_config = config.copy()
        config['ckan.plugins'] = 'stats'
        cls.app = _get_test_app()

    @classmethod
    def teardown_class(cls):
        config.clear()
        config.update(cls._original_config)
