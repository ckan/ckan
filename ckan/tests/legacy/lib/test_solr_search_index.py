# encoding: utf-8

import pytest
import pysolr
from ckan.common import config
import ckan.lib.search as search
from ckan.tests.legacy import (
    CreateTestData,
    setup_test_search_index,
    is_search_supported,
)


class TestSolrConfig(object):
    """
    Make sure that solr is enabled for this ckan instance.
    """

    def test_solr_url_exists(self):

        if not is_search_supported():
            pytest.skip("Search not supported")

        conn = search.make_connection()
        try:
            # solr.SolrConnection.query will throw a socket.error if it
            # can't connect to the SOLR instance
            q = conn.search(q="*:*", rows=1)
        except pysolr.SolrError as e:
            if not config.get("solr_url"):
                raise AssertionError(
                    "Config option 'solr_url' needs to be defined in this CKAN's development.ini. Default of %s didn't work: %s"
                    % (search.DEFAULT_SOLR_URL, e)
                )
            else:
                raise AssertionError(
                    "SOLR connection problem. Connection defined in development.ini as: solr_url=%s Error: %s"
                    % (config["solr_url"], e)
                )


class TestSolrSearch(object):
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db, clean_index):
        setup_test_search_index()
        CreateTestData.create_search_test_data()
        self.solr = search.make_connection()
        self.fq = ' +site_id:"%s" ' % config["ckan.site_id"]
        search.rebuild()

    def test_0_indexing(self):
        """
        Make sure that all packages created by CreateTestData.create_search_test_data
        have been added to the search index.
        """
        results = self.solr.search(q="*:*", fq=self.fq)
        assert len(results) == 6, len(results)

    def test_1_basic(self):
        results = self.solr.search(q="sweden", fq=self.fq)
        result_names = sorted([r["name"] for r in results])
        if not result_names:
            pytest.xfail("No datasets found")
        assert [u"se-opengov", u"se-publications"] == result_names
