import re

from pylons import config

from ckan.lib.helpers import json
from ckan.lib.helpers import literal
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData
from test_form import BaseFormsApiCase, Api1TestCase, Api2TestCase

# NB: This file tests the original package_gov form, which is moving
#     to the dgu repo, so this can go there too soon.

class PackageFixturesBase:
    def create(self, **kwargs):
        CreateTestData.create_arbitrary(self.pkgs,
                                        extra_user_names=[self.user_name],
                                        **kwargs)

    def delete(self):
        CreateTestData.delete()

class GovFixtures(PackageFixturesBase):
    user_name = 'tester'
    
    @property
    def pkgs(self):
        if not hasattr(self, '_pkgs'):
            self._pkgs = [
    {
     'name':u'private-fostering-england-2009',
     'title':u'Private Fostering',
     'notes':u'Figures on children cared for and accommodated in private fostering arrangements, England, Year ending 31 March 2009',
     'resources':[{'url':u'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000859/SFR17_2009_tables.xls',
                  'format':u'XLS',
                  'description':u'December 2009 | http://www.statistics.gov.uk/hub/id/119-36345'},
                  {'url':u'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000860/SFR17_2009_key.doc',
                  'format':u'DOC',
                  'description':u'http://www.statistics.gov.uk/hub/id/119-34565'}],
     'url':u'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000859/index.shtml',
     'author':u'DCSF Data Services Group',
     'author_email':u'statistics@dcsf.gsi.gov.uk',
     'license':u'ukcrown',
     'tags':u'children fostering',
     'extras':{
        'external_reference':u'DCSF-DCSF-0024',
        'date_released':u'2009-07-30',
        'date_updated':u'2009-07-30',
        'update_frequency':u'annual',
        'geographic_granularity':u'regional',
        'geographic_coverage':u'100000: England',
        'department':u'Department for Education',
        'temporal_granularity':u'year',
        'temporal_coverage-from':u'2008-6',
        'temporal_coverage-to':u'2009-6',
        'national_statistic':u'yes',
        'precision':u'Numbers to nearest 10, percentage to nearest whole number',
        'taxonomy_url':u'',
        'agency':u'',
        'import_source':u'ONS-Jan-09',
        }
     },
    {'name':u'weekly-fuel-prices',
     'title':u'Weekly fuel prices',
     'notes':u'Latest price as at start of week of unleaded petrol and diesel.',
     'resources':[{'url':u'', 'format':u'XLS', 'description':u''}],
     'url':u'http://www.decc.gov.uk/en/content/cms/statistics/source/prices/prices.aspx',
     'author':u'DECC Energy Statistics Team',
     'author_email':u'energy.stats@decc.gsi.gov.uk',
     'license':u'ukcrown',
     'tags':u'fuel prices',
     'extras':{
        'external_reference':u'DECC-DECC-0001',
        'date_released':u'2009-11-24',
        'date_updated':u'2009-11-24',
        'update_frequency':u'weekly',
        'geographic_granularity':u'national',
        'geographic_coverage':u'111100: United Kingdom (England, Scotland, Wales, Northern Ireland)',
        'department':u'Department of Energy and Climate Change',
        'temporal_granularity':u'weeks',
        'temporal_coverage-from':u'2008-11-24',
        'temporal_coverage-to':u'2009-11-24',
        'national_statistic':u'yes',
        'import_source':u'DECC-Jan-09',
        }
     }
                ]
        return self._pkgs


class FormsApiTestCase(BaseFormsApiCase):

    @classmethod
    def setup_class(self):
        self.fixtures = GovFixtures()
        self.fixtures.create()
        self.pkg_dict = self.fixtures.pkgs[0]
        self.package_name = self.pkg_dict['name']

    @classmethod
    def teardown_class(self):
        self.fixtures.delete()

    def test_get_package_create_form(self):
        form = self.get_package_create_form(package_form='gov')
        self.assert_formfield(form, 'Package--name', '')
        self.assert_formfield(form, 'Package--title', '')
        self.assert_not_formfield(form, 'Package--version', '')
        self.assert_formfield(form, 'Package--url', '')
        self.assert_formfield(form, 'Package--notes', '')
        self.assert_formfield(form, 'Package--resources-0-url', '')
        self.assert_formfield(form, 'Package--resources-0-format', '')
        self.assert_formfield(form, 'Package--resources-0-description', '')
        self.assert_formfield(form, 'Package--resources-0-hash', '')
        self.assert_formfield(form, 'Package--resources-0-id', '')
        self.assert_formfield(form, 'Package--resources-0-alt_url', '')
        self.assert_formfield(form, 'Package--resources-0-size', '')
        self.assert_formfield(form, 'Package--author', '')
        self.assert_formfield(form, 'Package--author_email', '')
        self.assert_formfield(form, 'Package--maintainer', '')
        self.assert_formfield(form, 'Package--maintainer_email', '')
        self.assert_formfield(form, 'Package--license_id', '')
        self.assert_not_formfield(form, 'Package--newfield0-key', '')
        self.assert_not_formfield(form, 'Package--newfield0-value', '')
        self.assert_not_formfield(form, 'Package--newfield1-key', '')
        self.assert_not_formfield(form, 'Package--newfield1-value', '')
        self.assert_not_formfield(form, 'Package--newfield2-key', '')
        self.assert_not_formfield(form, 'Package--newfield2-value', '')
        self.assert_not_formfield(form, 'Package--extras-date_update_future-key', '')
        self.assert_not_formfield(form, 'Package--extras-date_update_future-value', '')

    def test_get_package_edit_form(self):
        package = self.get_package_by_name(self.package_name)
        form = self.get_package_edit_form(package.id, package_form='gov')
        prefix = 'Package-%s-' % package.id
        self.assert_formfield(form, prefix + 'name', package.name)
        self.assert_formfield(form, prefix + 'external_reference', package.extras.get('external_reference'))
        self.assert_formfield(form, prefix + 'categories', package.extras.get('categories', ''))
        expected_values = dict([(key, value) for key, value in package.extras.items()])
        expected_values['temporal_coverage-to'] = '6/2009'
        expected_values['temporal_coverage-from'] = '6/2008'
        expected_values['temporal_granularity'] = 'other'
        expected_values['temporal_granularity-other'] = 'year'
        expected_values['date_updated'] = '30/7/2009'
        expected_values['date_released'] = '30/7/2009'
        expected_values['national_statistic'] = 'True'
        del expected_values['geographic_coverage'] # don't test here
#        del expected_values['external_reference']
        del expected_values['import_source']
        for key, value in expected_values.items():
            self.assert_formfield(form, prefix + key, value)

    def test_get_package_edit_form_restrict(self):
        package = self.get_package_by_name(self.package_name)
        form = self.get_package_edit_form(package.id, package_form='gov', restrict=True)
        prefix = 'Package-%s-' % package.id
        self.assert_not_formfield(form, prefix + 'name', package.name)
        self.assert_formfield(form, prefix + 'notes', package.notes)
        for key in ('department', 'national_statistic'):
            value = package.extras[key]
            self.assert_not_formfield(form, prefix + key, value)
        

class TestFormsApi1(Api1TestCase, FormsApiTestCase): pass

class TestFormsApi2(Api2TestCase, FormsApiTestCase): pass


class EmbeddedFormTestCase(BaseFormsApiCase):
    '''Tests the form as it would be used embedded in dgu html.'''

    @classmethod
    def setup_class(self):
        model.repo.init_db()
        self.fixtures = GovFixtures()
        self.fixtures.create()
        self.pkg_dict = self.fixtures.pkgs[0]
        self.package_name = self.pkg_dict['name']
        test_user = self.get_user_by_name(unicode(self.fixtures.user_name))
        self.apikey_header_name = config.get('apikey_header_name', 'X-CKAN-API-Key')
        self.extra_environ = {
            self.apikey_header_name : str(test_user.apikey)
        }
        

    @classmethod
    def teardown_class(self):
        self.fixtures.delete()
        # XXX can we remove the above?
        model.repo.clean_db()

    def _insert_into_field_tag(self, form_html, field_name, tag_name, tag_insertion):
        '''Finds the tag for a package field and inserts some html into it.'''
        form_html, num_replacements = re.subn(
            '(<%s[^>]* id="Package-.{0,36}-%s" .*) ?((value)|(name)=[^>]*>)' % \
            (tag_name, field_name),
            r'\1 class="disabled" readonly \2', form_html)
        assert num_replacements == 1, num_replacements
        return form_html

    def form_from_res(self, res):
        assert not "<html>" in str(res.body), "The response is an HTML doc, not just a form: %s" % str(res.body)

##        res.body = self._insert_into_field_tag(res.body, 'name', 'input', 'class="disabled" readonly')
##        res.body = self._insert_into_field_tag(res.body, 'department', 'select', 'disabled="disabled" readonly')
##        res.body = self._insert_into_field_tag(res.body, 'national_statistic', 'input', 'disabled="disabled" readonly')
        res.body = '''
<html>
  </body>
    <form method="post">
        %s
        <input type="submit">
    </form>
  </body>
</html>
''' % res.body

        return res.forms[0]

    def test_submit_package_create_form_valid(self):
        package_name = u'new_name'
        assert not self.get_package_by_name(package_name)
        form = self.get_package_create_form(package_form='gov')
        res = self.post_package_create_form(form=form, package_form='gov', name=package_name)
        self.assert_header(res, 'Location')
        assert not json.loads(res.body)
        self.assert_header(res, 'Location', 'http://localhost'+self.package_offset(package_name))
        pkg = self.get_package_by_name(package_name)
        assert pkg
        
    def test_submit_package_edit_form_valid(self):
        package_name = self.package_name
        pkg = self.get_package_by_name(package_name)
        new_title = u'New Title'
        form = self.get_package_edit_form(pkg.id, package_form='gov')
        res = self.post_package_edit_form(pkg.id, form=form, title=new_title, package_form='gov')
        # TODO work out if we need the Location header or not
#        self.assert_header(res, 'Location')
        assert not json.loads(res.body), res.body
#        self.assert_header(res, 'Location', 'http://localhost'+self.package_offset(package_name))
        pkg = self.get_package_by_name(package_name)
        assert pkg.title == new_title, pkg

    def test_submit_package_edit_form_valid_restrict(self):
        package_name = self.package_name
        pkg = self.get_package_by_name(package_name)
        new_title = u'New Title 2'
        form = self.get_package_edit_form(pkg.id, package_form='gov', restrict=True)
        res = self.post_package_edit_form(pkg.id, form=form, title=new_title, package_form='gov', restrict=True)
        assert not json.loads(res.body), res.body
        pkg = self.get_package_by_name(package_name)
        assert pkg.title == new_title, pkg

    def test_create_package(self):
        res = self.get_package_create_form()
        # TODO finish this test

    # TODO add other tests in from test_form.py

class TestEmbeddedFormApi1(Api1TestCase, EmbeddedFormTestCase): pass

class TestEmbeddedFormApi2(Api2TestCase, EmbeddedFormTestCase): pass
