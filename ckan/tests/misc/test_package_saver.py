from ckan.tests import *
import ckan.forms
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData
from ckan.lib.package_saver import PackageSaver

package_form = ''

class TestPreview(TestController):

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_new(self):
        params = {u'name':u'testname',
                  u'title':u'testtitle',
            u'url':u'testurl',
            u'resources':[[u'dlu1c', u'tf1c', u'', u''],
                          [u'dlu2c', u'tf2c', u'', u''],
                          ],
            u'notes':u'testnotes',
            u'version':u'testversion',
            u'tags':u'one three',
            u'license_id':u'4',
            u'extras':{u'key1':u'value1', u'key3':u'value3'},
                  }
        fs = ckan.forms.get_fieldset(is_admin=False, basic=False, package_form=package_form)
        data = ckan.forms.add_to_package_dict(ckan.forms.get_package_dict(fs=fs), params)
        fs = fs.bind(model.Package, data=data)
        pkg = PackageSaver()._preview_pkg(fs, '', '')

        self._check_preview_pkg(pkg, params)
        assert not model.Package.by_name(u'testname')

    def test_edit(self):
        CreateTestData.create_arbitrary(
            {u'name':u'name_before',
             u'title':u'title_before',
             u'url':u'testurl',
             u'resources':[{'url':'dlu1', 'format':'tf1'},
                           {'url':'dlu2', 'format':'tf2'},
                           ],
             u'notes':u'testnotes',
             u'version':u'testversion',
             u'tags':['one', 'two'],
             u'license':'OKD Compliant::Other',
             u'extras':{'key1':'value1', 'key2':'value2'},
             }
            )

        pkg = model.Package.by_name(u'name_before')
        params = {
            u'name':u'name_after',
            u'title':u'title_after',
            u'url':u'testurl',
            u'resources':[[u'dlu1c', u'tf1c', u'', u''],
                          [u'dlu2c', u'tf2c', u'', u''],
                          ],
            u'notes':u'testnotes',
            u'version':u'testversion',
            u'tags':u'one three',
            u'license_id':u'4',
            u'extras':{u'key1':u'value1', u'key3':u'value3'},
            }
        fs = ckan.forms.get_fieldset(is_admin=False, basic=False, package_form=package_form)
        data = ckan.forms.strip_ids_from_package_dict(ckan.forms.add_to_package_dict(ckan.forms.get_package_dict(pkg=pkg, fs=fs), params, pkg.id), pkg.id)
        fs = fs.bind(model.Package, data=data)
#        fs.session = None # explicitly forget about the pkg's session before
        pkg2 = PackageSaver()._preview_pkg(fs, u'name_before', pkg.id)
        self._check_preview_pkg(pkg2, params)

        # Check package is unchanged
        assert model.Package.by_name(u'name_before')
        assert not model.Package.by_name(u'name_after')

    def _check_preview_pkg(self, pkg, params):
        for key, value in params.items():
            if key == u'license_id':
                assert pkg.license_id == int(value)
#                assert pkg.license.name == model.Session.query(model.License).get(int(value))
            elif key == u'tags':
                reqd_tags = value.split()
                assert len(pkg.tags) == len(reqd_tags)
                for tag in pkg.tags:
                    assert tag.name in reqd_tags
            elif key == u'resources':
                assert pkg.resources[0].url == value[0][0]
                assert pkg.resources[0].format == value[0][1]
                assert pkg.resources[1].url == value[1][0]
                assert pkg.resources[1].format == value[1][1]
            else:
                assert getattr(pkg, key) == value, \
                       'Package has "%s"="%s" when it should be %s' % \
                       (key, getattr(pkg, key), value)
        
