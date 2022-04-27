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
        assert not result.exit_code, result.output
        search_result = helpers.call_action(u'package_search', q=u"After")
        assert search_result[u'count'] == 1

        # Clear and defer commit
        result = cli.invoke(ckan, [u'search-index', u'rebuild', '-e', '-c'])
        print(result.output)
        assert not result.exit_code
        search_result = helpers.call_action(u'package_search', q=u"After")
        assert search_result[u'count'] == 1

    @pytest.mark.ckan_config("ckan.search.remove_deleted_packages", True)
    def test_no_index_deleted_package(self, cli):
        """ Deleted packages should not be in search index. """
        factories.Dataset(title="Deleted package", id="deleted-pkg")
        helpers.call_action("package_delete", id="deleted-pkg")
        search_result = helpers.call_action('package_search', q="Deleted")
        assert search_result[u'count'] == 0

    @pytest.mark.ckan_config("ckan.search.remove_deleted_packages", True)
    def test_no_index_deleted_package_rebuild(self, cli):
        """ Deleted packages should not be in search index after rebuild. """
        factories.Dataset(title="Deleted package", id="deleted-pkg")
        helpers.call_action("package_delete", id="deleted-pkg")
        result = cli.invoke(ckan, ['search-index', 'rebuild'])
        assert not result.exit_code, result.output
        search_result = helpers.call_action('package_search', q="Deleted")
        assert search_result[u'count'] == 0

    @pytest.mark.ckan_config("ckan.search.remove_deleted_packages", False)
    def test_index_deleted_package(self, cli):
        """ Deleted packages should be in search index if ckan.search.remove_deleted_packages """
        dataset = factories.Dataset(title="Deleted package", id="deleted-pkg")
        helpers.call_action("package_delete", id="deleted-pkg")
        search_result = helpers.call_action('package_search', q="Deleted", include_deleted=True)
        assert search_result[u'count'] == 1
        assert search_result[u'results'][0]['id'] == dataset['id']
        # should be removed after purge
        helpers.call_action("dataset_purge", id="deleted-pkg")
        search_result = helpers.call_action('package_search', q="Deleted", include_deleted=True)
        assert search_result[u'count'] == 0

    @pytest.mark.ckan_config("ckan.search.remove_deleted_packages", False)
    def test_index_deleted_package_rebuild(self, cli):
        """ Deleted packages should be in search index after rebuild if ckan.search.remove_deleted_packages """
        dataset = factories.Dataset(title="Deleted package", id="deleted-pkg")
        helpers.call_action("package_delete", id="deleted-pkg")
        result = cli.invoke(ckan, ['search-index', 'rebuild'])
        assert not result.exit_code, result.output
        search_result = helpers.call_action('package_search', q="Deleted", include_deleted=True)
        assert search_result[u'count'] == 1
        assert search_result[u'results'][0]['id'] == dataset['id']
        # should be removed after purge
        helpers.call_action("dataset_purge", id="deleted-pkg")
        search_result = helpers.call_action('package_search', q="Deleted", include_deleted=True)
        assert search_result[u'count'] == 0

    @pytest.mark.ckan_config("ckan.search.remove_deleted_packages", False)
    def test_deleted_only_visible_for_right_users(self):
        """ If we index deleted datasets, we still needs to preserve
            privacy for private datasets. """

        user1 = factories.User()
        user2 = factories.User()
        org1 = factories.Organization(user=user1)
        org2 = factories.Organization(user=user2)
        dataset1 = factories.Dataset(
            name="dataset-user-1",
            user=user1,
            private=True,
            owner_org=org1["name"],
            state="deleted"
        )
        dataset2 = factories.Dataset(
            name="dataset-user-2",
            user=user2,
            private=True,
            owner_org=org2["name"],
            state="deleted"
        )

        search_results_1 = helpers.call_action(
            "package_search",
            {"user": user1["name"], "ignore_auth": False},
            include_private=True,
            include_deleted=True
        )
        results_1 = search_results_1["results"]

        assert [r["name"] for r in results_1] == [dataset1['name']]

        search_results_2 = helpers.call_action(
            "package_search",
            {"user": user2["name"], "ignore_auth": False},
            include_private=True,
            include_deleted=True
        )
        results_2 = search_results_2["results"]

        assert [r["name"] for r in results_2] == [dataset2['name']]

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
        assert not result.exit_code, result.output
        search_result = helpers.call_action(u'package_search', q=u"package")
        assert search_result[u'count'] == 1

        # Restore removed dataset and make sure all dataset are there
        result = cli.invoke(ckan,
                            [u'search-index', u'rebuild', dataset[u'id']])
        assert not result.exit_code, result.output
        search_result = helpers.call_action(u'package_search', q=u"package")
        assert search_result[u'count'] == 2

        # Remove one package from index and test `check` tool
        result = cli.invoke(ckan, [u'search-index', u'clear', another_dataset[u'id']])
        result = cli.invoke(ckan, [u'search-index', u'check'])
        assert not result.exit_code, result.output
        assert u'1 out of 2' in result.output
        search_result = helpers.call_action(u'package_search', q=u"package")
        assert search_result[u'count'] == 1

        # One can view data from index using CLI
        result = cli.invoke(ckan, [u'search-index', u'show', dataset[u'id']])
        assert not result.exit_code, result.output
        assert u'First package' in result.output
        assert u'Second package' not in result.output

        # Only search index is checked, not actual data in DB
        result = cli.invoke(ckan,
                            [u'search-index', u'show', another_dataset[u'id']])
        assert result.exit_code

        result = cli.invoke(ckan, [u'search-index', u'rebuild', u'-o'])
        assert not result.exit_code, result.output
        search_result = helpers.call_action(u'package_search', q=u"package")
        assert search_result[u'count'] == 2
