import os

from pylons import config

from ckan.tests import *
import ckan.model as model

EXAMPLES_DIR = 'ckan/tests/misc/'
EXAMPLE_TESTFILE_FILEPATH = os.path.join(config['here'], EXAMPLES_DIR, 'test_importer_example')
FULL_TESTFILE_FILEPATH = os.path.join(config['here'], EXAMPLES_DIR, 'test_importer_full')
XL_EXTENSION = '.xls'
CSV_EXTENSION = '.csv'
EXTENSIONS = [CSV_EXTENSION, XL_EXTENSION]

DEFAULT_USER = 'annafan'

# Only run this if xlrd is installed!
class _TestImporter(TestController):

    @classmethod
    def setup_class(self):
        model.repo.rebuild_db()
        CreateTestData.create()
        assert model.User.by_name(unicode(DEFAULT_USER))

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_0_index(self):
        offset = url_for(controller='importer')
        res = self.app.get(offset)
        assert 'Importer' in res, res

    def test_1_not_logged_in(self):
        res = self._submit_file(EXAMPLE_TESTFILE_FILEPATH + XL_EXTENSION, username=None, status=302)

    def test_1_not_logged_in_midway(self):
        res = self._submit_file(EXAMPLE_TESTFILE_FILEPATH + XL_EXTENSION, status=200)
        res_ = self._strip_res(res)
        assert 'Import Preview' in res, res_
        res = self._import(res, 'test', username=None, status=302)
        pkg = model.Package.by_name(u'wikipedia')
        assert not pkg

    def test_2_import_example_testfile(self):
        res = self._submit_file(EXAMPLE_TESTFILE_FILEPATH + XL_EXTENSION, status=200)
        res_ = self._strip_res(res)
        assert 'Import Preview' in res, res_
        assert '2 packages read' in res, res_
        assert 'wikipedia' in res_, res_
        assert 'tviv' in res_, res_
        res = self._import(res, 'test', status=200)
        assert 'Imported 2 packages' in res, self.main_div(res)

    # TODO get working: overwriting existing package
    def _test_3_import_full_testfile(self):
        res = self._submit_file(FULL_TESTFILE_FILEPATH + XL_EXTENSION, status=200)
        res_ = self._strip_res(res)
        assert 'Import Preview' in res, res_
        assert '2 packages read' in res, res_
        assert 'name: annakarenina' in res_, res_
        assert 'name: warandpeace' in res_, res_
        res = self._import(res, 'test', status=200)
        assert 'Imported 2 packages' in res, self.main_div(res)

    def _submit_file(self, filepath, username=DEFAULT_USER, status=None):
        assert os.path.exists(filepath)
        filebuf = open(filepath, 'rb').read()
        offset = url_for(controller='importer', action='preview')
        upload_file = ('file', filepath, filebuf)
        extra_environ = {'REMOTE_USER':username} if username else {}
        res = self.app.post(offset, upload_files=([upload_file]),
                            extra_environ=extra_environ,
                            status=status)
        return res
        
    def _import(self, res, log_message, username=DEFAULT_USER, status=None):
        form = res.forms[0]
        form['log_message'] = log_message
        extra_environ = {'REMOTE_USER':username} if username else {}
        res = form.submit('import', extra_environ=extra_environ,
                          status=status)
        if not status or status == 200:
            assert 'Import Result' in res, self.main_div(res)
        return res

    def _strip_res(self, res):
        return self.main_div(res).replace('<strong>', '').replace('</strong>', '')
        
