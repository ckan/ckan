import os

from pylons import config

import ckan.model as model
import ckan.getdata.data4nr as data4nr

test_data=os.path.join(config['here'], 'ckan/tests/getdata/samples/data4nr.csv')
test_data2=os.path.join(config['here'], 'ckan/tests/getdata/samples/data4nr2.csv')

class TestBasic:
    @classmethod
    def setup_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        self.data = data4nr.Data4Nr()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_load_data(self):
        assert model.Session.query(model.Package).count() == 0
        self.data.load_csv_into_db(test_data)
        model.Session.remove()
        assert model.Session.query(model.Package).count() == 6, model.Session.query(model.Package).count()

    def test_name_munge(self):
        def test_munge(title, expected_munge):
            munge = self.data._munge(title)
            assert munge == expected_munge, 'Got %s not %s' % (munge, expected_munge)
        test_munge('Adult participation in learning', 'adult_participation_in_learning')
        test_munge('Alcohol Profile: Alcohol-specific hospital admission, males', 'alcohol_profile_-_alcohol-specific_hospital_admission_males')
        test_munge('Age and limiting long-term illness by NS-SeC', 'age_and_limiting_long-term_illness_by_ns-sec')

    def test_temporal_coverage(self):
        def test(in_, out_from, out_to):
            out = self.data._parse_temporal_coverage(in_)
            assert out == (unicode(out_from), unicode(out_to)), out
        test('2003/04 to 2005/06', '2003', '2006')
        test('2000 to 2006', '2000', '2006')
        test('1998/99 to 2004/05', '1998', '2005')
        test('2003-05, 2007', '2003', '2007')
        test('2001', '2001', '2001')
        test('1996-1998 to 2005-2007 (3 year rolling averages)', '1996', '2007')
        test('1996-1998 to 2005-2007 (3 year rolling averages)', '1996', '2007')
        test('2007/08', '2007', '2008')
        test('2006-2007', '2006', '2007')
        test('2008 (using 2003 data)', '2008', '2008')
        test('Combined data for 2004/05 to 2006/07', '2004', '2007')
        test('(Data from different timepoints between 1999/00 and 2001/02)', '1999', '2002')
        test('2004 (using 2001 data)', '2004', '2004')
        test('October 2008 to June 2009', '2008', '2009')
        test('01/08/04 to 31/07/07', '2004', '2007')
        test('April 2005 - March 2006 to April 2006 - March 2007', '2005', '2007')
        test('2002-2009 combined', '2002', '2009')
        test('2004/05, to 2008/09', '2004', '2009')
        
class TestData:
    @classmethod
    def setup_class(self):
        self.data = data4nr.Data4Nr()
        self.data.load_csv_into_db(test_data)

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_fields(self):
        names = [pkg.name for pkg in model.Session.query(model.Package).all()]
        pkg1 = model.Package.by_name(u'age_and_limiting_long-term_illness_by_ns-sec')
        pkg2 = model.Package.by_name(unicode(self.data._munge('Adults with physical disabilities helped to live at home')))
        pkg3 = model.Package.by_name(unicode(self.data._munge('Suicide mortality rates')))
        assert pkg1, names
        assert pkg2, names
        assert pkg3, names
        assert pkg1.title == 'Age and limiting long-term illness by NS-SeC', pkg1.title
        assert pkg1.author == 'Nomis', pkg1.author
        assert pkg1.url == 'http://www.data4nr.net/resources/719/', pkg1.url
        assert len(pkg1.resources) == 1
        res = pkg1.resources[0]
        assert res.url == 'https://www.nomisweb.co.uk/query/construct/summary.asp?mode=construct&version=0&dataset=62', pkg1.resources
        assert res.description == 'Can be accessed through advanced query and wizard query. Access using the cell tab.'
        assert 'Age and limiting long-term illness by NS-SeC. Census Area Statistics Table CAS024' in pkg1.notes, pkg1.notes
        assert 'Source: Census 2001' in pkg1.notes, pkg1.notes
        assert pkg1.extras['department'] == '', pkg1.extras['department']
        assert pkg2.extras['department'] == 'Department of Health', pkg2.extras['department']
        assert 'Publisher: Nomis' in pkg1.notes
        assert pkg1.extras['geographic_coverage'] == '101000: England, Wales', pkg1.extras['geographic_coverage']
        assert 'Geographic coverage: England and Wales' in pkg1.notes, pkg1.notes
        assert 'Geographies: Lower Layer Super Output Area (LSOA), Middle Layer Super Output Area (MSOA), Local Authority District (LAD), Government Office Region (GOR), National, Parliamentary Constituency, Urban area' in pkg1.notes, pkg1.notes
        assert pkg1.extras['temporal_coverage_from'] == '2001', pkg1.extras['temporal_coverage_from']
        assert pkg2.extras['temporal_coverage_from'] == '2001', pkg2.extras['temporal_coverage_from']
        assert pkg3.extras['temporal_coverage_from'] == '1996', pkg3.extras['temporal_coverage_from']        
        assert pkg3.extras['temporal_coverage_to'] == '2007', pkg3.extras['temporal_coverage_to']
        assert not pkg1.extras['national_statistic'], pkg1.extras['national_statistic']
        assert 'Time coverage: 2001' in pkg1.notes, pkg1.notes
        assert 'Time coverage: 2001/02' in pkg2.notes, pkg2.notes
        assert 'Time coverage: 1996-1998 to 2005-2007 (3 year rolling averages)' in pkg3.notes, pkg3.notes
        assert pkg1.extras['update_frequency'] == 'Every 10 years', pkg1.extras['update_frequency']

        tag_names = [tag.name for tag in pkg1.tags]
        assert 'department_for_children_schools_and_families' not in tag_names, tag_names
        assert 'illness' in tag_names, tag_names
        assert 'england' not in tag_names, tag_names
        assert 'england_and_wales' not in tag_names, tag_names
        assert len(tag_names) > 1, tag_names
        assert 'UK Crown Copyright with data.gov.uk rights' in pkg1.license.title, pkg1.license.title
        assert pkg1.extras['external_reference'] == 'DATA4NR-719', pkg1.extras['external_reference']

        assert model.Group.by_name(u'ukgov') in pkg1.groups
        assert pkg1.extras['import_source'].startswith('DATA4NR'), pkg1.extras['import_source']

class TestDataTwice:
    @classmethod
    def setup_class(self):
        data = data4nr.Data4Nr()
        data.load_csv_into_db(test_data)
        data.load_csv_into_db(test_data2)

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_packages(self):
        q = model.Session.query(model.Package).filter_by(name=u'age_and_limiting_long-term_illness_by_ns-sec')
        assert q.count() == 1, q.count()
        pkg = q.one()
        assert pkg.title == 'Age and limiting long-term illness by NS-SeC', pkg.title
        assert pkg.notes.startswith('CHANGED'), pkg.notes
        assert len(pkg.resources) == 1, pkg.resources
        assert pkg.resources[0].url.startswith('CHANGED'), pkg.resources
        tag_names = [tag.name for tag in pkg.tags]
        assert 'census' in tag_names, tag_names
        assert 'illness' in tag_names, tag_names
        assert len(tag_names) > 1, tag_names
