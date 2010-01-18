import os

from pylons import config

import ckan.model as model
import ckan.getdata.ons_hub as data_getter

test_data=os.path.join(config['here'], 'ckan/tests/getdata/samples/ons_hub_sample.xml')
test_data2=os.path.join(config['here'], 'ckan/tests/getdata/samples/ons_hub_sample2.xml')

class TestBasic:
    @classmethod
    def setup_class(self):
        self.data = data_getter.Data()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_load_data(self):
        q = model.Session.query(model.Package)
        assert q.count() == 0
        self.data.load_xml_into_db(test_data)
        assert q.count() == 6, q.count()

    def test_title(self):
        def test(xml_title, expected_title, expected_release):
            title, release = self.data._split_title(xml_title)
            assert title == expected_title, 'Got %s not %s' % (title, expected_title)
            assert release == expected_release, 'Got %s not %s' % (release, expected_release)
        test('UK Trade - November 2009', 'UK Trade', 'November 2009')
        test('United Kingdom Economic Accounts - Q3 2009', 'United Kingdom Economic Accounts', 'Q3 2009')
        test('Hospital Episode Statistics: Admitted patient care - Provisional Monthly HES for Admitted patient care and outpatient data April - September 2009/10', 'Hospital Episode Statistics: Admitted patient care', 'Provisional Monthly HES for Admitted patient care and outpatient data April - September 2009/10')
        test('Excess winter deaths in Wales - 2008-09 (provisional)', 'Excess winter deaths in Wales', '2008-09 (provisional)')
        test('House Price Index - November 2009 - experimental', 'House Price Index', 'November 2009 - experimental')
        test('Probation statistics brief - July - September 2009', 'Probation statistics brief', 'July - September 2009')
        
class TestData:
    @classmethod
    def setup_class(self):
        data = data_getter.Data()
        data.load_xml_into_db(test_data)

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_fields(self):
        q = model.Session.query(model.Package)
        names = [pkg.name for pkg in q.all()]
        pkg1 = model.Package.by_name(u'uk_official_holdings_of_international_reserves')
        cereals = model.Package.by_name(u'cereals_and_oilseeds_production_harvest')
        custody = model.Package.by_name(u'end_of_custody_licence_release_and_recalls')
        assert pkg1, names
        assert cereals, names
        assert custody, names
        assert pkg1.title == 'UK Official Holdings of International Reserves', pkg1.title
        assert pkg1.notes.startswith("Monthly breakdown for government's net reserves, detailing gross reserves and gross liabilities."), pkg1.notes
        assert len(pkg1.resources) == 1, pkg1.resources
        assert pkg1.resources[0].url == 'http://www.hm-treasury.gov.uk/national_statistics.htm', pkg1.resources[0]
        assert pkg1.resources[0].description == 'December 2009 | http://www.statistics.gov.uk/hub/id/119-36345'
        assert len(custody.resources) == 2, custody.resources
        assert custody.resources[0].url == 'http://www.justice.gov.uk/publications/endofcustodylicence.htm', custody.resources[0]
        assert custody.resources[0].description == 'November 2009 | http://www.statistics.gov.uk/hub/id/119-36836', custody.resources[0].description
        assert custody.resources[1].url == 'http://www.justice.gov.uk/publications/endofcustodylicence.htm', custody.resources[0]
        assert custody.resources[1].description == 'December 2009 | http://www.statistics.gov.uk/hub/id/119-36838', custody.resources[1].description
        assert pkg1.extras['date_released'] == u'2010-01-06', pkg1.extras['date_released']
        assert pkg1.extras['department'] == u"Her Majesty's Treasury", pkg1.extras['department']
        assert cereals.extras['department'] == u"Department for Environment, Food and Rural Affairs", cereals.extras['department']
        assert custody.extras['department'] == u"Ministry of Justice", custody.extras['department']
        assert u"Source agency: HM Treasury" in pkg1.notes, pkg1.notes
        assert pkg1.extras['categories'] == 'Economy', pkg1.extras['category']
        assert pkg1.extras['geographic_coverage'] == '111100: United Kingdom (England, Scotland, Wales, Northern Ireland)', pkg1.extras['geographic_coverage']
        assert pkg1.extras['national_statistic'] == 'no', pkg1.extras['national_statistic']
        assert cereals.extras['national_statistic'] == 'yes', cereals.extras['national_statistic']
        assert custody.extras['national_statistic'] == 'no', custody.extras['national_statistic']
        assert 'Designation: Official Statistics not designated as National Statistics' in custody.notes
        assert pkg1.extras['geographical_granularity'] == 'UK and GB', pkg1.extras['geographical_granularity']
        assert 'Language: English' in pkg1.notes, pkg1.notes
        def check_tags(pkg, tags_list):            
            pkg_tags = [tag.name for tag in pkg.tags]
            for tag in tags_list:
                assert tag in pkg_tags, "Couldn't find tag '%s' in tags: %s" % (tag, pkg_tags)
        check_tags(pkg1, ('economics-and-finance', 'reserves', 'currency', 'assets', 'liabilities', 'gold', 'economy', 'government-receipts-and-expenditure', 'public-sector-finance'))
        check_tags(cereals, ('environment', 'farming'))
        check_tags(custody, ('public-order-justice-and-rights', 'justice-system', 'prisons'))
        assert 'Alternative title: UK Reserves' in pkg1.notes, pkg1.notes
        
        assert pkg1.extras['external_reference'] == u'ONSHUB', pkg1.extras['external_reference']
        assert 'Crown Copyright' in pkg.license.name, pkg.license.name
        assert pkg1.extras['update_frequency'] == u'monthly', pkg1.extras['update_frequency']
        assert custody.extras['update_frequency'] == u'monthly', custody.extras['update_frequency']
        assert pkg1.author == u"Her Majesty's Treasury", pkg1.author
        assert cereals.author == u'Department for Environment, Food and Rural Affairs', cereals.author
        assert custody.author == u'Ministry of Justice', custody.author


class TestDataTwice:
    @classmethod
    def setup_class(self):
        data = data_getter.Data()
        data.load_xml_into_db(test_data)
        data.load_xml_into_db(test_data2) # same packages, slightly different

    def test_packages(self):
        pkg = model.Package.by_name(u'uk_official_holdings_of_international_reserves')
        assert pkg.title == 'UK Official Holdings of International Reserves', pkg.title
        assert pkg.notes.startswith('CHANGED'), pkg.notes
        assert len(pkg.resources) == 1, pkg.resources
        assert 'CHANGED' in pkg.resources[0].description, pkg.resources
