import tempfile

from ckan.tests.legacy import TestController, CreateTestData
import ckan.model as model
import ckan.lib.dumper as dumper
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
        assert 'datahub.io/download' in res, res
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
