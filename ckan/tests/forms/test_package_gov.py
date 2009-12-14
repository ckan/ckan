import ckan.model as model
import ckan.forms
from ckan.tests import *
from ckan.lib.create_test_data import CreateTestData
from pylons import config

def _get_blank_param_dict(pkg=None, fs=None):
    return ckan.forms.get_package_dict(pkg, blank=True, fs=fs)

class TestForm:
    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create_gov_test_data()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_0_field_names(self):
        fs = ckan.forms.package_gov_fs
        pkg = model.Package.by_name(u'private-fostering-england-2009')
        fs = fs.bind(pkg)
        out = fs.render()
        assert out
        # check the right fields are rendered
        assert 'Revision' not in out, out
        assert 'Title' in out, out
        assert 'Extras' not in out
        assert 'External reference' in out, out

    def test_1_field_values(self):
        fs = ckan.forms.package_gov_fs
        pkg = model.Package.by_name(u'private-fostering-england-2009')
        fs = fs.bind(pkg)
        out = fs.render()
        assert out
        assert 'Private Fostering' in fs.title.render(), fs.title.render()
        assert 'Private Fostering' in fs.title.render_readonly(), fs.title.render_readonly()
        assert 'DCSF-DCSF-0024' in fs.external_reference.render(), fs.external_reference.render()
        assert 'DCSF-DCSF-0024' in fs.external_reference.render_readonly(), fs.external_reference.render_readonly()
        assert '30/7/2009' in fs.date_released.render(), fs.date_released.render()
        assert '30/7/2009' in fs.date_released.render_readonly(), fs.date_released.render_readonly()
        dept = fs.department.render()
        assert '<select' in dept, dept
        assert 'option value="Department for Children, Schools and Families" selected=' in dept, dept
        assert 'option value="other">' in dept, dept
        assert 'Other:' in dept, dept
        assert 'value=""' in dept, dept
        assert 'Department:</strong> Department for Children, Schools and Families' in fs.department.render_readonly(), fs.department.render_readonly()

    def test_2_field_department_none(self):
        # Create package
        model.repo.new_revision()
        pkg = model.Package(name=u'test3')
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(u'test3')
        fs = ckan.forms.package_gov_fs
        fs = fs.bind(pkg)
        out = fs.render()
        assert out
        dept = fs.department.render()
        dept_readonly = fs.department.render_readonly()
        assert '<select' in dept, dept
        assert 'selected' not in dept, dept # nothing selected
        assert 'Other:' in dept, dept
        assert 'value=""' in dept, dept
        assert 'Department:</strong> <br/>' in dept_readonly, dept_readonly

    def test_2_field_department_other(self):
        # Create package
        model.repo.new_revision()
        pkg = model.Package(name=u'test2')
        pkg.extras = {u'department':u'Not on the list'}
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(u'test2')
        fs = ckan.forms.package_gov_fs
        fs = fs.bind(pkg)
        out = fs.render()
        assert out
        dept = fs.department.render()
        dept_readonly = fs.department.render_readonly()
        assert '<select' in dept, dept
        assert 'option value="Department for Children, Schools and Families">' in dept, dept # i.e. not selected
        assert 'option value="other" selected="' in dept, dept # selected
        assert 'Other:' in dept, dept
        assert 'value="Not on the list"' in dept, dept
        assert 'Department:</strong> Not on the list' in dept_readonly, dept_readonly
        
        
    def test_3_sync_new(self):
        newtagname = 'newtagname'
        indict = _get_blank_param_dict(fs=ckan.forms.package_gov_fs)
        indict['Package--name'] = u'testname'
        indict['Package--notes'] = u'some new notes'
        indict['Package--tags'] = u'russian tolstoy, ' + newtagname,
        indict['Package--license_id'] = '1'
        indict['Package--external_reference'] = u'123'
        indict['Package--deparment'] = u'testdept'
        indict['Package--date_released'] = u'27/11/2008'
        indict['Package--resources-0-url'] = u'http:/1'
        indict['Package--resources-0-format'] = u'xml'
        indict['Package--resources-0-description'] = u'test desc'
        fs = ckan.forms.package_gov_fs.bind(model.Package, data=indict)

        model.repo.new_revision()
        fs.sync()
        model.repo.commit_and_remove()

        outpkg = model.Package.by_name(u'testname')
        assert outpkg.notes == indict['Package--notes']

        # test tags
        taglist = [ tag.name for tag in outpkg.tags ]
        assert u'russian' in taglist, taglist
        assert u'tolstoy' in taglist, taglist
        assert newtagname in taglist

        # test licenses
        assert outpkg.license
        assert indict['Package--license_id'] == str(outpkg.license.id), outpkg.license.id

        # test resources
        assert len(outpkg.resources) == 1, outpkg.resources
        res = outpkg.resources[0]
        assert res.url == u'http:/1', res.url
        assert res.description == u'test desc', res.description
        assert res.format == u'xml', res.format

        # test gov fields
        extra_keys = outpkg.extras.keys()
        reqd_extras = {'external_reference':indict['Package--external_reference'],
                       'department':indict['Package--department'],
                       'date_released':'2008-11-27',
                       }
        for reqd_extra_key, reqd_extra_value in reqd_extras.items():
            assert reqd_extra_key in extra_keys, 'Key "%s" not found in extras %r' % (reqd_extra_key, extra_keys)
            assert outpkg.extras[reqd_extra_key] == reqd_extra_value, \
                 'Extra %s should equal %s but equals %s' % \
                 (reqd_extra_key, reqd_extra_value,
                  outpkg.extras[reqd_extra_key])

    def test_4_sync_update(self):
        # create initial package
        init_data = [{
            'name':'test_sync',
            'title':'test_title',
            'extras':{
              'external_reference':'ref123',
              'department':'dosac',
              'date_released':'2008-11-28',
              },
            }]
        CreateTestData.create_arbitrary(init_data)
        pkg = model.Package.by_name(u'test_sync')
        assert pkg

        # edit it with form parameters
        indict = _get_blank_param_dict(fs=ckan.forms.package_gov_fs)
        indict['Package--name'] = u'testname2'
        indict['Package--notes'] = u'some new notes'
        indict['Package--tags'] = u'russian, tolstoy',
        indict['Package--license_id'] = '1'
        indict['Package--external_reference'] = u'123'
        indict['Package--deparment'] = u'testdept'
        indict['Package--date_released'] = u'27/11/2008'
        indict['Package--resources-0-url'] = u'http:/1'
        indict['Package--resources-0-format'] = u'xml'
        indict['Package--resources-0-description'] = u'test desc'
        fs = ckan.forms.package_gov_fs.bind(model.Package, data=indict)

        model.repo.new_revision()
        fs.sync()
        model.repo.commit_and_remove()

        outpkg = model.Package.by_name(u'testname')
        assert outpkg.notes == indict['Package--notes']

        # test tags
        taglist = [ tag.name for tag in outpkg.tags ]
        assert u'russian' in taglist, taglist
        assert u'tolstoy' in taglist, taglist

        # test licenses
        assert outpkg.license
        assert indict['Package--license_id'] == str(outpkg.license.id), outpkg.license.id

        # test resources
        assert len(outpkg.resources) == 1, outpkg.resources
        res = outpkg.resources[0]
        assert res.url == u'http:/1', res.url
        assert res.description == u'test desc', res.description
        assert res.format == u'xml', res.format

        # test gov fields
        extra_keys = outpkg.extras.keys()
        reqd_extras = {'external_reference':indict['Package--external_reference'],
                       'department':indict['Package--department'],
                       'date_released':'2008-11-27',
                       }
        for reqd_extra_key, reqd_extra_value in reqd_extras.items():
            assert reqd_extra_key in extra_keys, 'Key "%s" not found in extras %r' % (reqd_extra_key, extra_keys)
            assert outpkg.extras[reqd_extra_key] == reqd_extra_value, \
                 'Extra %s should equal %s but equals %s' % \
                 (reqd_extra_key, reqd_extra_value,
                  outpkg.extras[reqd_extra_key])
        


class TestDate:
    def test_0_form_to_db(self):
        out = ckan.forms.DateType().form_to_db('27/2/2008')
        assert out == '2008-02-27', out
        out = ckan.forms.DateType().form_to_db('2/2008')
        assert out == '2008-02', out
        out = ckan.forms.DateType().form_to_db('2008')
        assert out == '2008', out

    def test_1_form_validator(self):
        assert ckan.forms.DateType().form_validator('25/2/2009') is None
        assert ckan.forms.DateType().form_validator('humpty')
        assert ckan.forms.DateType().form_validator('2135')
        assert ckan.forms.DateType().form_validator('345')
        assert ckan.forms.DateType().form_validator('2000BC')
        assert ckan.forms.DateType().form_validator('45/2009')
        assert ckan.forms.DateType().form_validator('-2/2009')
        assert ckan.forms.DateType().form_validator('35/3/2009')
        assert ckan.forms.DateType().form_validator('') is None
        
    def test_2_db_to_form(self):
        out = ckan.forms.DateType().db_to_form('2008-02-27')
        assert out == '27/2/2008', out
        out = ckan.forms.DateType().db_to_form('2008-02')
        assert out == '2/2008', out
        out = ckan.forms.DateType().db_to_form('2008')
        assert out == '2008', out
        out = ckan.forms.DateType().db_to_form('humpty')
        assert out == 'humpty', out
        out = ckan.forms.DateType().db_to_form('27/2/2008')
        assert out == '27/2/2008', out
        
