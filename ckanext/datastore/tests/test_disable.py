# encoding: utf-8

import nose

from ckan.common import config
import ckan.plugins as p
import nose.tools as t


class TestDisable(object):

    @t.raises(KeyError)
    def test_disable_sql_search(self):
        config['ckan.datastore.sqlsearch.enabled'] = False
        with p.use_plugin('datastore') as the_plugin:
            print(p.toolkit.get_action('datastore_search_sql'))
        config['ckan.datastore.sqlsearch.enabled'] = True

    def test_enabled_sql_search(self):
        config['ckan.datastore.sqlsearch.enabled'] = True
        with p.use_plugin('datastore') as the_plugin:
            p.toolkit.get_action('datastore_search_sql')
