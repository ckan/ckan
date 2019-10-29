# encoding: utf-8

from ckan import model
from ckan.lib.cli import SearchIndexCommand
from ckan.lib.create_test_data import CreateTestData
import pytest
from ckan.lib.search import index_for, query_for


class FakeOptions:
    def __init__(self, **kwargs):
        for key in kwargs:
            setattr(self, key, kwargs[key])


class TestSearch:
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db):
        self.search = SearchIndexCommand("search-index")
        self.index = index_for(model.Package)
        self.query = query_for(model.Package)
        CreateTestData.create()

    def test_clear_and_rebuild_index(self):

        # Clear index
        self.search.args = ()
        self.search.options = FakeOptions()
        self.search.clear()

        self.query.run({"q": "*:*"})

        assert self.query.count == 0

        # Rebuild index
        self.search.args = ()
        self.search.options = FakeOptions(
            only_missing=False,
            force=False,
            refresh=False,
            commit_each=False,
            quiet=False,
        )
        self.search.rebuild()
        pkg_count = (
            model.Session.query(model.Package)
            .filter(model.Package.state == u"active")
            .count()
        )

        self.query.run({"q": "*:*"})

        assert self.query.count == pkg_count

        pkg_count = (
            model.Session.query(model.Package)
            .filter(model.Package.state == u"active")
            .count()
        )

        # Clear index for annakarenina
        self.search.args = ("clear annakarenina").split()
        self.search.options = FakeOptions()
        self.search.clear()

        self.query.run({"q": "*:*"})

        assert self.query.count == pkg_count - 1

        # Rebuild index for annakarenina
        self.search.args = ("rebuild annakarenina").split()
        self.search.options = FakeOptions(
            only_missing=False, force=False, refresh=False, commit_each=False
        )
        self.search.rebuild()

        self.query.run({"q": "*:*"})

        assert self.query.count == pkg_count
