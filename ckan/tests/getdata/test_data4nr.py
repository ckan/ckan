import ckan.model as model
import ckan.getdata.data4nr as data4nr

test_data='ckan/tests/getdata/samples/data4nr.csv'
test_data2='ckan/tests/getdata/samples/data4nr2.csv'

class TestBasic:
    @classmethod
    def setup_class(self):
        self.data = data4nr.Data4Nr()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_load_data(self):
        assert model.Package.query.count() == 0
        self.data.load_csv_into_db(test_data)
        assert model.Package.query.count() == 3, model.Package.query.all()

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
        data = data4nr.Data4Nr()
        data.load_csv_into_db(test_data)

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_fields(self):
        names = [pkg.name for pkg in model.Package.query.all()]
        print names
        pkg1 = model.Package.query.filter_by(name=u'age_and_limiting_long-term_illness_by_ns-sec_2001').one()
        assert pkg1
        assert pkg1.title == 'Age and limiting long-term illness by NS-SeC', pkg1.title
        assert pkg1.author == 'Nomis', pkg1.author
        assert pkg1.url == 'http://www.data4nr.net/resources/719/', pkg1.url
        assert pkg1.download_url == 'https://www.nomisweb.co.uk/query/construct/summary.asp?mode=construct&version=0&dataset=62', pkg1.download_url
        assert 'Age and limiting long-term illness by NS-SeC. Census Area Statistics Table CAS024' in pkg1.notes, pkg1.notes
        assert 'Source: Census 2001' in pkg1.notes, pkg1.notes
        assert 'Geographic coverage: England and Wales' in pkg1.notes, pkg1.notes
        assert 'Geographies: Lower Layer Super Output Area (LSOA), Middle Layer Super Output Area (MSOA), Local Authority District (LAD), Government Office Region (GOR), National, Parliamentary Constituency, Urban area' in pkg1.notes, pkg1.notes
        assert 'Time coverage: 2001' in pkg1.notes, pkg1.notes
        extras = pkg1._extras
        assert len(extras) == 2, extras
        extra = model.PackageExtra.query.filter_by(package=pkg1, key=u'source').one()
        assert extra == extras[u'source']
        assert extra.value == u'Census 2001', extra.value 
        extra = model.PackageExtra.query.filter_by(package=pkg1, key=u'update frequency').one()
        assert extra == extras[u'update frequency']
        assert extra.value == u'Every 10 years', extra.value
        tag_names = set()
        [tag_names.add(tag.name) for tag in pkg.tags]
        assert 'department_for_children_schools_and_families' in tag_names, tag_names
        assert 'england' in tag_names, tag_names
        assert len(tag_names) == 2
        assert 'Crown Copyright' in pkg.license.name, pkg.license.name

class TestDataTwice:
    @classmethod
    def setup_class(self):
        data = data4nr.Data4Nr()
        data.load_csv_into_db(test_data)
        data.load_csv_into_db(test_data2)

    def test_packages(self):
        q = model.Package.query.filter_by(name=u'age_and_limiting_long-term_illness_by_ns-sec_2001')
        assert q.count() == 1, q.count()
        pkg = q.one()
        assert pkg.title == 'Age and limiting long-term illness by NS-SeC', pkg.title
        assert pkg.notes.startswith('CHANGED'), pkg.notes
        assert len(pkg._extras) == 2, pkg._extras
        q = model.PackageExtra.query.filter_by(package=pkg, key=u'source')
        assert q.count() == 1, q.all()
        extra = q.one()
        assert extra == pkg._extras[u'source']
        assert extra.value == u'CHANGED Census 2001', extra.value 
        tag_names = set()
        [tag_names.add(tag.name) for tag in pkg.tags]
        assert 'changed_england_and_wales' in tag_names, tag_names
        assert 'census' in tag_names, tag_names
        assert 'illness' in tag_names, tag_names
        assert len(tag_names) == 3
