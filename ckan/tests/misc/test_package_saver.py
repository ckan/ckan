from ckan.tests import *
import ckan.forms
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData
from ckan.lib.package_saver import PackageSaver
from ckan.tests.pylons_controller import PylonsTestCase

class TestPreview(PylonsTestCase):

    @classmethod
    def setup_class(self):
        model.repo.init_db()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    params = {
        u'name':u'name_after',
        u'title':u'title_after',
        u'url':u'testurl',
        u'resources':[{'url':u'dlu1c', 'format':u'tf1c'},
                      {'url':u'dlu2c', 'format':u'tf2c'},
                      ],
        u'notes':u'testnotes',
        u'version':u'testversion',
        u'tags':u'one three',
        u'license_id':u'gpl-3.0',
        u'extras':{u'key1':u'value1', u'key3':u'value3'},
        }

    def test_new(self):
        fs = ckan.forms.get_standard_fieldset(is_admin=False, user_editable_groups=[])
        data = ckan.forms.add_to_package_dict(
            ckan.forms.get_package_dict(fs=fs, user_editable_groups=[]), self.params)
        fs = fs.bind(model.Package, data=data)

        assert not model.Package.by_name(u'testname')

    def test_edit(self):
        CreateTestData.create_arbitrary(
            {u'name':u'name_before',
             u'title':u'title_before',
             u'url':u'testurl',
             u'resources':[{'url':'dlu1', 'format':'tf1'},
                           ],
             u'notes':u'testnotes',
             u'version':u'testversion',
             u'tags':['one', 'two'],
             u'license':'gpl-3.0',
             u'extras':{'key1':'value1', 'key2':'value2'},
             }
            )

        pkg = model.Package.by_name(u'name_before')
        fs = ckan.forms.get_standard_fieldset(is_admin=False, user_editable_groups=[])
        data =  ckan.forms.add_to_package_dict(
                ckan.forms.get_package_dict(pkg=pkg, fs=fs, user_editable_groups=[]), self.params,
                    pkg.id)
        fs = fs.bind(pkg, data=data)

        # Check nothing has changed in the model
        assert model.Package.by_name(u'name_before')
        assert not model.Package.by_name(u'name_after')
        assert not model.Tag.by_name(u'three')
        resources = model.Session.query(model.Resource).filter_by(url=u'dlu2c').first()
        assert resources is None, resources
        
