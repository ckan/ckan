# -*- coding: utf-8 -*-

import pytest

import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan.cli.cli import ckan


@pytest.mark.usefixtures(u"clean_db", u"clean_index")
class TestSearchIndex(object):
    def test_search_index_rebuild(self, cli):
        """Direct update on package won't be reflected in search results till
        re-index.

        """
        dataset = factories.Dataset(title=u"Before rebuild")
        model.Session.query(model.Package).filter_by(id=dataset[u'id']).update(
            {u'title': u'After update'})
        model.Session.commit()

        search_result = helpers.call_action(u'package_search', q=u"After")
        assert search_result[u'count'] == 0

        result = cli.invoke(ckan, [u'search-index', u'rebuild'])
        assert not result.exit_code
        search_result = helpers.call_action(u'package_search', q=u"After")
        assert search_result[u'count'] == 1

    def test_test_main_operations(self, cli):
        """Create few datasets, clear index, rebuild it - make sure search results
        are always reflect correct state of index.

        """
        # Create two datasets and check if they are available in search results
        dataset = factories.Dataset(title=u"First package")
        another_dataset = factories.Dataset(title=u"Second package")
        search_result = helpers.call_action(u'package_search', q=u"package")
        assert search_result[u'count'] == 2

        # Remove one dataset
        result = cli.invoke(ckan, [u'search-index', u'clear', dataset[u'id']])
        assert not result.exit_code
        search_result = helpers.call_action(u'package_search', q=u"package")
        assert search_result[u'count'] == 1

        # Restore removed dataset and make sure all dataset are there
        result = cli.invoke(ckan,
                            [u'search-index', u'rebuild', dataset[u'id']])
        assert not result.exit_code
        search_result = helpers.call_action(u'package_search', q=u"package")
        assert search_result[u'count'] == 2

        # Remove one package from index and test `check` tool
        result = cli.invoke(ckan, [u'search-index', u'clear', another_dataset[u'id']])
        result = cli.invoke(ckan, [u'search-index', u'check'])
        assert not result.exit_code
        assert u'1 out of 2' in result.output
        search_result = helpers.call_action(u'package_search', q=u"package")
        assert search_result[u'count'] == 1

        # One can view data from index using CLI
        result = cli.invoke(ckan, [u'search-index', u'show', dataset[u'id']])
        assert not result.exit_code
        assert u'First package' in result.output
        assert u'Second package' not in result.output

        # Only search index is checked, not actual data in DB
        result = cli.invoke(ckan,
                            [u'search-index', u'show', another_dataset[u'id']])
        assert result.exit_code

        result = cli.invoke(ckan, [u'search-index', u'rebuild', u'-o'])
        assert not result.exit_code
        search_result = helpers.call_action(u'package_search', q=u"package")
        assert search_result[u'count'] == 2
