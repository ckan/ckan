# encoding: utf-8

from nose.tools import assert_equal

import pysolr
from ckan.common import config
from ckan import model
import ckan.lib.search as search
from ckan.tests.legacy import TestController, CreateTestData, setup_test_search_index, is_search_supported

class TestSolrConfig(TestController):
    """
    Make sure that solr is enabled for this ckan instance.
    """
    def test_solr_url_exists(self):
        if not is_search_supported():
            from nose import SkipTest
            raise SkipTest("Search not supported")

        conn = search.make_connection()
        try:
            # solr.SolrConnection.query will throw a socket.error if it
            # can't connect to the SOLR instance
            q = conn.search(q="*:*", rows=1)
        except pysolr.SolrError as e:
            if not config.get('solr_url'):
                raise AssertionError("Config option 'solr_url' needs to be defined in this CKAN's development.ini. Default of %s didn't work: %s" % (search.DEFAULT_SOLR_URL, e))
            else:
                raise AssertionError('SOLR connection problem. Connection defined in development.ini as: solr_url=%s Error: %s' % (config['solr_url'], e))


class TestSolrSearch:
    @classmethod
    def setup_class(cls):
        setup_test_search_index()
        CreateTestData.create_search_test_data()
        cls.solr = search.make_connection()
        cls.fq = " +site_id:\"%s\" " % config['ckan.site_id']
        search.rebuild()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        search.index_for('Package').clear()

    def test_0_indexing(self):
        """
        Make sure that all packages created by CreateTestData.create_search_test_data
        have been added to the search index.
        """
        results = self.solr.search(q='*:*', fq=self.fq)
        assert len(results) == 6, len(results)

    def test_1_basic(self):
        results = self.solr.search(q='sweden', fq=self.fq)
        result_names = sorted([r['name'] for r in results])

        assert_equal([u'se-opengov', u'se-publications'], result_names)
