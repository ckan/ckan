import os
from nose import tools as nosetools

from pylons import config

import ckan.tests.helpers as h
import ckan.plugins as p


class TestUpdateConfig(h.FunctionalTestBase):

    '''
    Tests for config settings from env vars, set in
    config.environment.update_config().
    '''

    ENV_VAR_LIST = [
        ('CKAN_SQLALCHEMY_URL', 'postgresql://mynewsqlurl/'),
        ('CKAN_DATASTORE_WRITE_URL', 'http://mynewdbwriteurl/'),
        ('CKAN_DATASTORE_READ_URL', 'http://mynewdbreadurl/'),
        ('CKAN_SOLR_URL', 'http://mynewsolrurl/solr'),
        ('CKAN_SITE_ID', 'my-site'),
        ('CKAN_DB', 'postgresql://mydeprectatesqlurl/')
    ]

    def _setup_env_vars(self):
        for env_var, value in self.ENV_VAR_LIST:
            os.environ.setdefault(env_var, value)
        # plugin.load() will force the config to update
        p.load()

    def teardown(self):
        for env_var, _ in self.ENV_VAR_LIST:
            if os.environ.get(env_var, None):
                del os.environ[env_var]
        # plugin.load() will force the config to update
        p.load()

    def test_update_config_env_vars(self):
        '''
        Setting an env var from the whitelist will set the appropriate option
        in config object.
        '''
        self._setup_env_vars()

        nosetools.assert_equal(config['solr_url'],
                               'http://mynewsolrurl/solr')
        nosetools.assert_equal(config['sqlalchemy.url'],
                               'postgresql://mynewsqlurl/')
        nosetools.assert_equal(config['ckan.datastore.write_url'],
                               'http://mynewdbwriteurl/')
        nosetools.assert_equal(config['ckan.datastore.read_url'],
                               'http://mynewdbreadurl/')
        nosetools.assert_equal(config['ckan.site_id'],
                               'my-site')

    def test_update_config_db_url_precidence(self):
        '''CKAN_SQLALCHEMY_URL in the env takes precidence over CKAN_DB'''
        os.environ.setdefault('CKAN_DB', 'postgresql://mydeprectatesqlurl/')
        os.environ.setdefault('CKAN_SQLALCHEMY_URL',
                              'postgresql://mynewsqlurl/')
        p.load()

        nosetools.assert_equal(config['sqlalchemy.url'],
                               'postgresql://mynewsqlurl/')
