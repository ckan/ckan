import ckan.model as model
import ckan.getdata.cospread as data_getter

test_data='ckan/tests/getdata/samples/cospread.csv'
test_data2='ckan/tests/getdata/samples/cospread2.csv' # same but with notes changed

class TestBasic:
    @classmethod
    def setup_class(self):
        self.data = data_getter.Data()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_load_data(self):
        assert model.Package.query.count() == 0
        self.data.load_csv_into_db(test_data)
        assert model.Package.query.count() == 3, model.Package.query.count()

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
        names = [pkg.name for pkg in model.Package.query.all()]
        pkg1 = model.Package.query.filter_by(name=u'child-protection-plan-england-2009').one()
        pkg2 = model.Package.query.filter_by(name=u'provision-children-under-5-england-2009').one()
        pkg3 = model.Package.query.filter_by(name=u'laboratory-tests-and-prices').one()
        assert pkg1
        assert pkg1.title == 'Child Protection Plan', pkg1.title
        assert pkg1.extras['co_id'] == u'DCSF-DCSF-0017', pkg1.extras
        assert pkg1.notes.startswith(u'Referrals, assessment and children and young people who are the subjects of child protection plans (on the child protection register) for year ending March 2009'), pkg1.notes
        val = u'17/09/2009'
#        assert pkg1.extras['date_released'] == val, pkg1.extras
        assert 'Date released: %s' % val in pkg1.notes, pkg1.notes
        val = u'40073'
#        assert pkg1.extras['date_updated'] == val, pkg1.extras
        assert 'Date updated: %s' % val in pkg1.notes, pkg1.notes
        val = u'Annually'
#        assert pkg1.extras['update_frequency'] == val, pkg1.extras
        assert 'Update frequency: %s' % val in pkg1.notes, pkg1.notes
        val = u'Local Authority'
#        assert pkg1.extras['geographical_granularity'] == val, pkg1.extras
        assert 'Geographical granularity: %s' % val in pkg1.notes, pkg1.notes
        tag_names = set()
        [tag_names.add(tag.name) for tag in pkg1.tags]
        assert 'england' in tag_names, tag_names
        assert 'northern_ireland' not in tag_names, tag_names
        val = u'Years'
#        assert pkg1.extras['temporal_granularity'] == val, pkg1.extras
        assert 'Temporal granularity: %s' % val in pkg1.notes, pkg1.notes
        val = u'XLS'
        assert 'File format: %s' % val in pkg1.notes, pkg1.notes
        val = u'Yes'
#        assert pkg1.extras['national_statistic'] == val, pkg1.extras
        assert 'National statistic: %s' % val in pkg1.notes, pkg1.notes
        val = u'Numbers rounded to nearest 100 if over 1,000, and to the nearest 10 otherwise.  Percentage to nearest whole number.'
#        assert pkg1.extras['precision'] == val, pkg1.extras
        assert 'Precision: %s' % val in pkg1.notes, pkg1.notes
        assert pkg1.url == 'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000873/index.shtml', pkg1.url
        assert not pkg1.resources, pkg1.resources # 2 of them, so goes in the notes
        assert pkg2.resources, pkg2.resources
        assert pkg2.resources[0].url == 'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000848/SFR11_2009tables.xls', pkg2.resources
        assert not pkg3.resources, pkg3.resources
        assert 'test.html' in pkg3.notes, pkg3.notes
        assert 'test.json' in pkg3.notes, pkg3.notes
        assert 'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000873/FINALAdditionalTables1to13.xls' in pkg1.notes, pkg1.notes
        assert 'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000873/NationalIndicatorTables.xls' in pkg1.notes, pkg1.notes
        assert 'Taxonomy URL: ' not in pkg1.notes, pkg1.notes
        val = u'Department for Children, Schools and Families'
        assert 'department-for-children-schools-and-families' in tag_names, tag_names
        assert 'Department: %s' % val in pkg1.notes, pkg1.notes
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
        q = model.Package.query.filter_by(name=u'child-protection-plan-england-2009')
        pkg = q.one()
        assert pkg.title == 'Child Protection Plan', pkg.title
        assert pkg.notes.startswith('CHANGED'), pkg.notes
        assert len(pkg._extras) == 2, pkg._extras
        q = model.PackageExtra.query.filter_by(package=pkg, key=u'co_id')
        assert q.count() == 1, q.all()
        extra = q.one()
        assert extra == pkg._extras[u'co_id']
        assert extra.value == u'DCSF-DCSF-0017', extra.value 
        tag_names = set()
        [tag_names.add(tag.name) for tag in pkg.tags]
        assert 'england' in tag_names, tag_names
        assert 'child-protection' in tag_names, tag_names
        assert len(tag_names) == 4, len(tag_names)

        q = model.Package.query.filter_by(name=u'provision-children-under-5-england-2009')
        pkg = q.one()
#        assert len(pkg.resources) == 1, pkg.resources
