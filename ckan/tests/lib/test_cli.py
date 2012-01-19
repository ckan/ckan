import os
import csv

from nose.tools import assert_equal

from ckan import model
from ckan.lib.cli import ManageDb
from ckan.lib.create_test_data import CreateTestData
from ckan.lib.helpers import json

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
