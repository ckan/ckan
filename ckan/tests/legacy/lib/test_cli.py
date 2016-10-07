# encoding: utf-8

import os
import csv

from nose.tools import assert_equal

from ckan import model
from ckan.lib.cli import ManageDb,SearchIndexCommand
from ckan.lib.create_test_data import CreateTestData
from ckan.common import json

from ckan.lib.search import index_for,query_for, clear_all


class FakeOptions():
    def __init__(self,**kwargs):
        for key in kwargs:
            setattr(self,key,kwargs[key])

class TestSearch:
    @classmethod
    def setup_class(cls):
        cls.search = SearchIndexCommand('search-index')
        cls.index = index_for(model.Package)
        cls.query = query_for(model.Package)
        CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_clear_and_rebuild_index(self):

        # Clear index
        self.search.args = ()
        self.search.options = FakeOptions()
        self.search.clear()

        self.query.run({'q':'*:*'})

        assert self.query.count == 0

        # Rebuild index
        self.search.args = ()
        self.search.options = FakeOptions(only_missing=False, force=False, refresh=False, commit_each=False, quiet=False)
        self.search.rebuild()
        pkg_count = model.Session.query(model.Package).filter(model.Package.state==u'active').count()

        self.query.run({'q':'*:*'})

        assert self.query.count == pkg_count

    def test_clear_and_rebuild_only_one(self):

        pkg_count = model.Session.query(model.Package).filter(model.Package.state==u'active').count()

        # Clear index for annakarenina
        self.search.args = ('clear annakarenina').split()
        self.search.options = FakeOptions()
        self.search.clear()

        self.query.run({'q':'*:*'})

        assert self.query.count == pkg_count - 1

        # Rebuild index for annakarenina
        self.search.args = ('rebuild annakarenina').split()
        self.search.options = FakeOptions(only_missing=False,force=False,refresh=False,commit_each=False)
        self.search.rebuild()

        self.query.run({'q':'*:*'})

        assert self.query.count == pkg_count
