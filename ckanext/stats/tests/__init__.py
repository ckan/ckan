# encoding: utf-8

import paste.fixture
from ckan.common import config
from ckan.config.middleware import make_app

class StatsFixture(object):

    @classmethod
    def setup_class(cls):
        cls._original_config = config.copy()
        config['ckan.plugins'] = 'stats'
        wsgiapp = make_app(config['global_conf'], **config)
        cls.app = paste.fixture.TestApp(wsgiapp)

    @classmethod
    def teardown_class(cls):
        config.clear()
        config.update(cls._original_config)
