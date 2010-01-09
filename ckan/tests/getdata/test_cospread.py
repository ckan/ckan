import os

from pylons import config

import ckan.model as model
import ckan.getdata.cospread as data_getter

test_data=os.path.join(config['here'], 'ckan/tests/getdata/samples/cospread.csv')
test_data2=os.path.join(config['here'], 'ckan/tests/getdata/samples/cospread2.csv')

class TestBasic:
    @classmethod
    def setup_class(self):
        self.data = data_getter.Data()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_load_data(self):
        assert model.Session.query(model.Package).count() == 0
        self.data.load_csv_into_db(test_data)
        assert model.Session.query(model.Package).count() == 3, model.Session.query(model.Package).count()

    def test_name_munge(self):
        def test_munge(title, expected_munge):
            munge = self.data._munge(title)
            assert munge == expected_munge, 'Got %s not %s' % (munge, expected_munge)
        test_munge('Adult participation in learning', 'adult_participation_in_learning')
        test_munge('Alcohol Profile: Alcohol-specific hospital admission, males', 'alcohol_profile_-_alcohol-specific_hospital_admission_males')
        test_munge('Age and limiting long-term illness by NS-SeC', 'age_and_limiting_long-term_illness_by_ns-sec')

class TestData:
    @classmethod
    def setup_class(self):
        data = data_getter.Data()
        data.load_csv_into_db(test_data)

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_fields(self):
        names = [pkg.name for pkg in model.Session.query(model.Package).all()]
        pkg1 = model.Session.query(model.Package).filter_by(name=u'child-protection-plan-england-2009').one()
        pkg2 = model.Session.query(model.Package).filter_by(name=u'provision-children-under-5-england-2009').one()
        pkg3 = model.Session.query(model.Package).filter_by(name=u'laboratory-tests-and-prices').one()
        assert pkg1
        assert pkg1.title == 'Child Protection Plan', pkg1.title
        assert pkg1.extras['external_reference'] == u'DCSF-DCSF-0017', pkg1.extras
        assert pkg1.notes.startswith(u'Referrals, assessment and children and young people who are the subjects of child protection plans (on the child protection register) for year ending March 2009'), pkg1.notes
        assert pkg1.extras['date_released'] == u'2009-09-17', pkg1.extras
        assert 'Date released:' not in pkg1.notes, pkg1.notes
        assert pkg1.extras['date_updated'] == u'2009-09-17', pkg1.extras
        assert 'Date updated:' not in pkg1.notes, pkg1.notes
        assert pkg1.extras['update_frequency'] == u'Annually', pkg1.extras
        assert 'Update frequency:' not in pkg1.notes, pkg1.notes
        assert pkg.extras['geographic_coverage'] == '100000: England', pkg.extras['geographic_coverage']
        assert 'Geographic coverage:' not in pkg1.notes, pkg1.notes
        assert pkg1.extras['geographical_granularity'] == u'local authority', pkg1.extras
        assert 'Geographical granularity:' not in pkg1.notes, pkg1.notes
        tag_names = set()
        [tag_names.add(tag.name) for tag in pkg1.tags]
        assert 'england' not in tag_names, tag_names
        assert 'northern_ireland' not in tag_names, tag_names
        assert pkg1.extras['temporal_granularity'] == u'years', pkg1.extras
        assert 'Temporal granularity:' not in pkg1.notes, pkg1.notes
        assert pkg1.extras['national_statistic'] == u'yes', pkg1.extras
        assert 'National statistic:' not in pkg1.notes, pkg1.notes
        val = u'Numbers rounded to nearest 100 if over 1,000, and to the nearest 10 otherwise.  Percentage to nearest whole number.'
        assert pkg1.extras['precision'] == val, pkg1.extras
        assert 'Precision:' not in pkg1.notes, pkg1.notes
        assert pkg1.url == 'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000873/index.shtml', pkg1.url
        assert len(pkg1.resources) == 2, pkg1.resources
        assert pkg1.resources[0].format == u'XLS', pkg1.resources[0].format
        assert 'File format:' not in pkg1.notes, pkg1.notes
        assert pkg2.resources, pkg2.resources
        assert pkg2.resources[0].url == 'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000848/SFR11_2009tables.xls', pkg2.resources
        assert len(pkg3.resources) == 2, pkg3.resources
        assert pkg3.resources[0].url == 'test.html', pkg3.resources
        assert pkg3.resources[1].url == 'test.json', pkg3.resources
        assert pkg1.resources[0].url == 'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000873/FINALAdditionalTables1to13.xls', pkg1.resources
        assert pkg1.resources[1].url == 'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000873/NationalIndicatorTables.xls', pkg1.resources
        assert pkg1.extras.get('taxonomy_url') == '', pkg1.extras
        assert pkg2.extras['taxonomy_url'] == 'http://www.dcsf.gov.uk/taxonomy.html', pkg1.extras['taxonomy_url']
        assert 'Taxonomy URL: ' not in pkg1.notes, pkg1.notes
        val = u'Department for Children, Schools and Families'
        assert 'department-for-children-schools-and-families' not in tag_names, tag_names
        assert pkg1.extras['department'] == val, pkg1.extras['department']
        assert 'Department:' not in pkg1.notes, pkg1.notes
        assert 'Agency responsible:' not in pkg1.notes, pkg1.notes
        assert pkg1.author == 'DCSF Data Services Group', pkg1.author
        assert pkg1.author_email == 'statistics@dcsf.gsi.gov.uk', pkg1.author_email
        assert not pkg1.maintainer, pkg1.maintainer
        assert not pkg1.maintainer_email, pkg1.maintainer_email
        assert 'Crown Copyright' in pkg.license.name, pkg.license.name
        for tag in ['child-protection']:
            assert tag in tag_names, '%s not in %s' % (tag, tag_names)


class TestDataTwice:
    @classmethod
    def setup_class(self):
        data = data_getter.Data()
        data.load_csv_into_db(test_data)
        data.load_csv_into_db(test_data2) # same packages, slightly different

    def test_packages(self):
        q = model.Session.query(model.Package).filter_by(name=u'child-protection-plan-england-2009')
        pkg = q.one()
        assert pkg.title == 'Child Protection Plan', pkg.title
        assert pkg.notes.startswith('CHANGED'), pkg.notes
        assert pkg.extras['external_reference'] == u'DCSF-DCSF-0017', pkg.extras['external_reference']
        tag_names = set()
        [tag_names.add(tag.name) for tag in pkg.tags]
        assert '000100: Northern Ireland' in pkg.extras['geographic_coverage'], pkg.extras
        assert 'child-protection' in tag_names, tag_names

        q = model.Session.query(model.Package).filter_by(name=u'provision-children-under-5-england-2009')
        pkg = q.one()
        assert len(pkg.resources) == 1, pkg.resources
