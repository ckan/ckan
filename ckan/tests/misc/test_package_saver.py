from ckan.tests import *
import ckan.forms
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData
from ckan.lib.package_saver import PackageSaver
from ckan.tests.pylons_controller import PylonsTestCase

class TestPreview(PylonsTestCase):

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
        fs = ckan.forms.get_standard_fieldset(is_admin=False)
        data = ckan.forms.add_to_package_dict(
            ckan.forms.get_package_dict(fs=fs), self.params)
        fs = fs.bind(model.Package, data=data)
        pkg = PackageSaver()._preview_pkg(fs, '', '')

        self._check_preview_pkg(pkg, self.params)
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
        fs = ckan.forms.get_standard_fieldset(is_admin=False)
        data =  ckan.forms.add_to_package_dict(
                ckan.forms.get_package_dict(pkg=pkg, fs=fs), self.params,
                    pkg.id)
        fs = fs.bind(pkg, data=data)
        pkg2 = PackageSaver()._preview_pkg(fs, u'name_before', pkg.id)
        self._check_preview_pkg(pkg2, self.params)

        # Check nothing has changed in the model
        assert model.Package.by_name(u'name_before')
        assert not model.Package.by_name(u'name_after')
        assert not model.Tag.by_name(u'three')
        resources = model.Session.query(model.PackageResource).filter_by(url=u'dlu2c').first()
        assert resources is None, resources

    def _check_preview_pkg(self, pkg, params):
        for key, value in params.items():
            if key == u'license':
                assert pkg.license_id == value
                assert pkg.license.id == value
            elif key == u'license_id':
                assert pkg.license_id == value
                assert pkg.license.id == value
            elif key == u'tags':
                reqd_tags = value.split()
                assert len(pkg.tags) == len(reqd_tags)
                for tag in pkg.tags:
                    assert tag.name in reqd_tags
            elif key == u'resources':
                assert pkg.resources[0].url == value[0]['url']
                assert pkg.resources[0].format == value[0]['format']
                assert pkg.resources[1].url == value[1]['url']
                assert pkg.resources[1].format == value[1]['format']
            else:
                assert getattr(pkg, key) == value, \
                       'Package has "%s"="%s" when it should be %s' % \
                       (key, getattr(pkg, key), value)
        
