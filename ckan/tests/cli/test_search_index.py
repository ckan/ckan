# -*- coding: utf-8 -*-

import pytest

import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan.cli.cli import ckan


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestSearchIndex(object):
    def test_search_index_rebuild(self, cli):
        """Direct update on package won't be reflected in search results till
        re-index.

        """
        dataset = factories.Dataset(title="Before rebuild")
        model.Session.query(model.Package).filter_by(id=dataset['id']).update(
            {'title': 'After update'})
        model.Session.commit()

        search_result = helpers.call_action('package_search', q="After")
        assert search_result['count'] == 0

        result = cli.invoke(ckan, ['search-index', 'rebuild'])
        assert not result.exit_code
        search_result = helpers.call_action('package_search', q="After")
        assert search_result['count'] == 1

        # Clear and defer commit
        result = cli.invoke(ckan, ['search-index', 'rebuild', '-e', '-c'])
        print(result.output)
        assert not result.exit_code
        search_result = helpers.call_action('package_search', q="After")
        assert search_result['count'] == 1

    def test_test_main_operations(self, cli):
        """Create few datasets, clear index, rebuild it - make sure search results
        are always reflect correct state of index.

        """
        # Create two datasets and check if they are available in search results
        dataset = factories.Dataset(title="First package")
        another_dataset = factories.Dataset(title="Second package")
        search_result = helpers.call_action('package_search', q="package")
        assert search_result['count'] == 2

        # Remove one dataset
        result = cli.invoke(ckan, ['search-index', 'clear', dataset['id']])
        assert not result.exit_code
        search_result = helpers.call_action('package_search', q="package")
        assert search_result['count'] == 1

        # Restore removed dataset and make sure all dataset are there
        result = cli.invoke(ckan,
                            ['search-index', 'rebuild', dataset['id']])
        assert not result.exit_code
        search_result = helpers.call_action('package_search', q="package")
        assert search_result['count'] == 2

        # Remove one package from index and test `check` tool
        result = cli.invoke(ckan, ['search-index', 'clear', another_dataset['id']])
        result = cli.invoke(ckan, ['search-index', 'check'])
        assert not result.exit_code
        assert '1 out of 2' in result.output
        search_result = helpers.call_action('package_search', q="package")
        assert search_result['count'] == 1

        # One can view data from index using CLI
        result = cli.invoke(ckan, ['search-index', 'show', dataset['id']])
        assert not result.exit_code
        assert 'First package' in result.output
        assert 'Second package' not in result.output

        # Only search index is checked, not actual data in DB
        result = cli.invoke(ckan,
                            ['search-index', 'show', another_dataset['id']])
        assert result.exit_code

        result = cli.invoke(ckan, ['search-index', 'rebuild', '-o'])
        assert not result.exit_code
        search_result = helpers.call_action('package_search', q="package")
        assert search_result['count'] == 2
