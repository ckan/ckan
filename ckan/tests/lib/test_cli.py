import os
import csv

from nose.tools import assert_equal

from ckan import model
from ckan.lib.cli import ManageDb,SearchIndexCommand
from ckan.lib.create_test_data import CreateTestData
from ckan.common import json

from ckan.lib.search import index_for,query_for

class TestDb:
    @classmethod
    def setup_class(cls):
        cls.db = ManageDb('db')
        CreateTestData.create()

        # delete warandpeace
        rev = model.repo.new_revision()
        model.Package.by_name(u'warandpeace').delete()
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_simple_dump_csv(self):
        csv_filepath = '/tmp/dump.tmp'
        self.db.args = ('simple-dump-csv %s' % csv_filepath).split()
        self.db.simple_dump_csv()
        assert os.path.exists(csv_filepath), csv_filepath
        f_obj = open(csv_filepath, "r")
        reader = csv.reader(f_obj)
        rows = [row for row in reader]
        assert_equal(rows[0][:3], ['id', 'name', 'title'])
        pkg_names = set(row[1] for row in rows[1:])
        assert 'annakarenina' in pkg_names, pkg_names
        assert 'warandpeace' not in pkg_names, pkg_names

    def test_simple_dump_json(self):
        json_filepath = '/tmp/dump.tmp'
        self.db.args = ('simple-dump-json %s' % json_filepath).split()
        self.db.simple_dump_json()
        assert os.path.exists(json_filepath), json_filepath
        f_obj = open(json_filepath, "r")
        rows = json.loads(f_obj.read())
        assert set(rows[0].keys()) > set(('id', 'name', 'title')), rows[0].keys()
        pkg_names = set(row['name'] for row in rows)
        assert 'annakarenina' in pkg_names, pkg_names
        assert 'warandpeace' not in pkg_names, pkg_names

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
        self.search.options = FakeOptions(only_missing=False,force=False,refresh=False,commit_each=False)
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
