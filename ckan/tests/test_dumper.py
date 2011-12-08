import tempfile
import os
from time import time

import ckan
from ckan.tests import *
import ckan.model as model
import ckan.lib.dumper as dumper
from ckan.lib.helpers import json
from ckan.lib.dumper import Dumper
simple_dumper = dumper.SimpleDumper()

class TestSimpleDump(TestController):

    @classmethod
    def setup_class(self):
        model.repo.rebuild_db()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_simple_dump_csv(self):
        dump_file = tempfile.TemporaryFile()
        simple_dumper.dump(dump_file, 'csv')
        dump_file.seek(0)
        res = dump_file.read()
        assert 'annakarenina' in res, res
        assert 'tolstoy' in res, res
        assert 'russian' in res, res
        assert 'genre' in res, res
        assert 'romantic novel' in res, res
        assert 'annakarenina.com/download' in res, res
        assert 'Index of the novel' in res, res
        assert 'joeadmin' not in res, res
        self.assert_correct_field_order(res)
        
    def test_simple_dump_json(self):
        dump_file = tempfile.TemporaryFile()
        simple_dumper.dump(dump_file, 'json')
        dump_file.seek(0)
        res = dump_file.read()
        assert 'annakarenina' in res, res
        assert '"russian"' in res, res
        assert 'genre' in res, res
        assert 'romantic novel' in res, res
        assert 'joeadmin' not in res, res
        self.assert_correct_field_order(res)

    def assert_correct_field_order(self, res):
        correct_field_order = ('id', 'name', 'title', 'version', 'url')
        field_position = [res.find('"%s"' % field) for field in correct_field_order]
        field_position_sorted = field_position[:]
        field_position_sorted.sort()
        assert field_position == field_position_sorted, field_position

class TestDumper(object):
# TODO this doesn't work on sqlite - we should fix this
    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()
        d = Dumper()
        ts = int(time())
        self.outpath = '/tmp/mytestdump-%s.js' % ts
        if os.path.exists(self.outpath):
            os.remove(self.outpath)
        d.dump_json(self.outpath)

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_dump(self):
        assert os.path.exists(self.outpath) 
        dumpeddata = json.load(open(self.outpath))
        assert dumpeddata['version'] == ckan.__version__
        tables = dumpeddata.keys()
        for key in ['Package', 'Tag', 'Group', 'Member', 'PackageExtra']:
            assert key in tables, '%r not in %s' % (key, tables)
        for key in ['User']:
            assert key not in tables, '%s should not be in %s' % (key, tables)
        assert len(dumpeddata['Package']) == 2, len(dumpeddata['Package'])
        assert len(dumpeddata['Tag']) == 3, len(dumpeddata['Tag'])
        assert len(dumpeddata['PackageRevision']) == 2, len(dumpeddata['PackageRevision'])
        assert len(dumpeddata['Group']) == 2, len(dumpeddata['Group'])

    # Disabled 22/9/09 because not used anymore
    def _test_load(self):
        model.repo.rebuild_db()
        model.repo.create_db()
        d = Dumper()
        d.load_json(self.outpath)
        assert len(model.Package.query.all()) == 2

