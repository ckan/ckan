import os
from nose import tools as nosetools

from pylons import config

import ckan.plugins as p


class TestUpdateConfig(object):

    '''
    Tests for config settings from env vars, set in
    config.environment.update_config().
    '''

    def test_update_config_solr_url(self):
        '''
        Setting the solr url as an env var will set the appropriate option in
        config object.
        '''
        nosetools.assert_equal(config['solr_url'],
                               'http://127.0.0.1:8983/solr')
        os.environ.setdefault('CKAN_SOLR_URL', 'http://mynewsolrurl/solr')
        # plugin.load() will force the config to update
        p.load()
        nosetools.assert_equal(config['solr_url'],
                               'http://mynewsolrurl/solr')

    def test_update_config_sqlalchemy_url(self):
        '''
        Setting the sqlalchemy url as an env var will set the appropriate
        option in config object.
        '''
        nosetools.assert_equal(config['sqlalchemy.url'],
                               'postgresql://ckan_default:pass@localhost/ckan_test')
        os.environ.setdefault('CKAN_SQLALCHEMY_URL',
                              'postgresql://mynewsqlurl/')
        # plugin.load() will force the config to update
        p.load()
        nosetools.assert_equal(config['sqlalchemy.url'],
                               'postgresql://mynewsqlurl/')

    def test_update_config_datastore_write_url(self):
        '''
        Setting the datastore write url as an env var will set the appropriate
        option in config object.
        '''
        nosetools.assert_equal(config['ckan.datastore.write_url'],
                               'postgresql://ckan_default:pass@localhost/datastore_test')
        os.environ.setdefault('CKAN_DATASTORE_WRITE_URL',
                              'http://mynewdbwriteurl/')
        # plugin.load() will force the config to update
        p.load()
        nosetools.assert_equal(config['ckan.datastore.write_url'],
                               'http://mynewdbwriteurl/')

    def test_update_config_datastore_read_url(self):
        '''
        Setting the datastore read url as an env var will set the appropriate
        option in config object.
        '''
        nosetools.assert_equal(config['ckan.datastore.read_url'],
                               'postgresql://datastore_default:pass@localhost/datastore_test')
        os.environ.setdefault('CKAN_DATASTORE_READ_URL',
                              'http://mynewdbreadurl/')
        # plugin.load() will force the config to update
        p.load()
        nosetools.assert_equal(config['ckan.datastore.read_url'],
                               'http://mynewdbreadurl/')

    def test_update_config_site_id(self):
        '''
        Setting the site id as an env var will set the appropriate option in
        config object.
        '''
        nosetools.assert_equal(config['ckan.site_id'], 'test.ckan.net')
        os.environ.setdefault('CKAN_SITE_ID', 'my-site')
        # plugin.load() will force the config to update
        p.load()
        nosetools.assert_equal(config['ckan.site_id'],
                               'my-site')
