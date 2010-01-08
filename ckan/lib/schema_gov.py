import re

__all__ = ['government_depts', 'geographic_granularity_options', 'temporal_granularity_options', 'category_options', 'region_options', 'region_groupings', 'tag_pool', 'suggest_tags', 'DateType', 'GeoCoverageType', 'expand_abbreviations']

government_depts_raw = """
Attorney General's Office
Cabinet Office
Central Office of Information
Charity Commission for England and Wales
Commissioners for the Reduction of the National Debt
Crown Estate
Crown Prosecution Service
Department for Business, Innovation and Skills
Department for Children, Schools and Families
Department for Communities and Local Government
Department for Culture, Media and Sport
Department for Environment, Food and Rural Affairs
Department for International Development
Department for Transport
Department for Work and Pensions
Department of Energy and Climate Change
Department of Health
Export Credits Guarantee Department
Food Standards Agency
Foreign and Commonwealth Office
Forestry Commission
Government Actuary's Department
Government Equalities Office
Her Majesty's Revenue and Customs
Her Majesty's Treasury
Home Office
Ministry of Defence
Ministry of Justice
National School of Government
Northern Ireland Office
Office for Standards in Education, Children's Services and Skills
Office of Fair Trading
Office of Gas and Electricity Markets
Office of Rail Regulation
Office of the Advocate General for Scotland
Office of the Leader of the House of Commons
Office of the Leader of the House of Lords
Office of the Parliamentary Counsel
Postal Services Commission
Public Works Loan Board
Revenue and Customs Prosecutions Office
Scotland Office
Serious Fraud Office
Treasury Solicitor's Department
UK Statistics Authority
UK Trade & Investment
Wales Office
Water Services Regulation Authority
"""
government_depts = []
for line in government_depts_raw.split('\n'):
    if line:
        government_depts.append(line.strip())

department_agency_abbreviations = {'DCSF':'Department for Children, Schools and Families', 'VLA':'Vetinary Laboratories Agency', 'MFA':'Marine and Fisheries Agency', 'CEFAS':'Centre of Environment, Fisheries and Aquaculture Science', 'FERA':'Food and Environment Research Agency', 'DEFRA':'Department for Environment, Food and Rural Affairs', 'CRB':'Criminal Records Bureau', 'UKBA':'UK Border Agency', 'IPS':'Identity and Passport Service', 'NPIA':'National Policing Improvement Agency', 'CIB':'Company Investigation Branch', 'IPO':'Intellectual Property Office'}

geographic_granularity_options = ['national', 'regional', 'local authority', 'ward', 'point']

temporal_granularity_options = ['years', 'months', 'weeks', 'days', 'hours', 'points']

category_options = ['Agriculture and Environment', 'Business and Energy', 'Children, Education and Skills', 'Crime and Justice', 'Economy', 'Government', 'Health and Social Care', 'Labour Market', 'People and Places', 'Population', 'Travel and Transport', 'Equality and Diversity', 'Migration']

region_options = ('England', 'Scotland', 'Wales', 'Northern Ireland', 'Overseas', 'Global')

region_groupings = {'United Kingdom':['England', 'Scotland', 'Wales', 'Northern Ireland'], 'Great Britain':['England', 'Scotland', 'Wales']}

tag_pool = ['accident', 'road', 'traffic', 'health', 'illness', 'disease', 'population', 'school', 'accommodation', 'children', 'married', 'emissions', 'benefit', 'alcohol', 'deaths', 'mortality', 'disability', 'unemployment', 'employment', 'armed forces', 'asylum', 'cancer', 'births', 'burglary', 'child', 'tax credit', 'criminal damage', 'drug', 'earnings', 'education', 'economic', 'fire', 'fraud', 'forgery', 'fuel', 'green', 'greenhouse gas', 'homeless', 'hospital', 'waiting list', 'housing', 'care', 'income', 'census', 'mental health', 'disablement allowance', 'jobseekers allowance', 'national curriculum', 'older people', 'living environment', 'higher education', 'living environment', 'school absence', 'local authority', 'carbon dioxide', 'energy', 'teachers', 'fostering', 'tide', 'gas', 'electricity', 'transport', 'veterinary', 'fishing', 'export', 'fisheries', 'pest', 'recycling', 'waste', 'crime', 'anti-social behaviour', 'police', 'refugee', 'identity card', 'immigration', 'planning', 'communities', 'lettings', 'finance', 'ethnicity', 'trading standards', 'trade', 'business', 'child protection']

tag_search_fields = ['name', 'title', 'notes', 'categories', 'agency']

class TagSuggester(object):
    @classmethod
    def _tag_munge(cls, name):
        return cls._munge(name).replace('_', '-').replace('--', '-')

    @classmethod
    def _munge(cls, name):
        # convert spaces to underscores
        name = re.sub(' ', '_', name).lower()        
        # convert symbols to dashes
        name = re.sub('[:]', '_-', name).lower()        
        name = re.sub('[/]', '-', name).lower()        
        # take out not-allowed characters
        name = re.sub('[^a-zA-Z0-9-_]', '', name).lower()
        # remove double underscores
        name = re.sub('__', '_', name).lower()                
        return name[:100]

    @classmethod
    def suggest_tags(cls, pkg_dict):
        tags = set()
        for field_name in tag_search_fields:
            text = pkg_dict[field_name]
            if text and isinstance(text, (str, unicode)):
                for keyword in tag_pool:
                    if keyword in text:
                        tags.add(cls._tag_munge(keyword))
        return list(tags)

suggest_tags = TagSuggester.suggest_tags

class DateType(object):
    '''Handles conversions between form and database as well as
    validation.'''
    date_match = re.compile('(\d+)([/\-.]\d+)?([/\-.]\d+)?')
    default_db_separator = '-'
    default_form_separator = '/'

    @classmethod
    def form_to_db(self, form_str):
        '27/2/2005 -> 2005-02-27'
        if not form_str:
            # Allow blank
            return u''
        err_str = 'Date must be format DD/MM/YYYY or DD/MM/YY.'
        match = self.date_match.match(form_str)
        if not match:
            raise TypeError('%s Date provided: "%s"' % (err_str, form_str))
        matched_date = ''.join([group if group else '' for group in match.groups()])
        if matched_date != form_str:
            raise TypeError('%s Matched only "%s"' % (err_str, matched_date))
        standard_date_fields = [] # integers, year first
        for match_group in match.groups()[::-1]:
            if match_group is not None:
                standard_date_fields.append(int(match_group.strip('/-.')))
        # Deal with 2 digit dates
        if standard_date_fields[0] > 0 and standard_date_fields[0] < 60:
            standard_date_fields[0] += 2000
        if standard_date_fields[0] >= 60 and standard_date_fields[0] < 100:
            standard_date_fields[0] += 1900
        # Check range of dates
        if standard_date_fields[0] < 1000 or standard_date_fields[0] > 2100:
            raise TypeError('%s Year of "%s" is outside range.' % (err_str, standard_date_fields[0]))
        if len(standard_date_fields) > 1 and (standard_date_fields[1] > 12 or standard_date_fields[1] < 1):
            raise TypeError('%s Month of "%s" is outside range.' % (err_str, standard_date_fields[0]))
        if len(standard_date_fields) > 2 and (standard_date_fields[2] > 31 or standard_date_fields[2] < 1):
            raise TypeError('%s Month of "%s" is outside range.' % (err_str, standard_date_fields[0]))
        str_date_fields = [] # strings, year first
        for i, digits in enumerate((4, 2, 2)):
            if len(standard_date_fields) > i:
                format_string = '%%0%sd' % digits
                str_date_fields.append(format_string % standard_date_fields[i])
        db_date = unicode(self.default_db_separator.join(str_date_fields))
        return db_date

    @staticmethod
    def form_validator(form_date_str, field=None):
        try:
            DateType.form_to_db(form_date_str)
        except TypeError, e:
            return e

    @classmethod
    def db_to_form(self, db_str):
        '2005-02-27 -> 27/2/2005 if correct format, otherwise, display as is.'
        if not db_str.strip():
            return db_str
        match = self.date_match.match(db_str)
        if not match:
            return db_str
        matched_date = ''.join([group if group else '' for group in match.groups()])
        if matched_date != db_str.strip():
            return db_str
        standard_date_fields = [] # integers, year first
        for match_group in match.groups():
            if match_group is not None:
                standard_date_fields.append(int(match_group.strip('/-.')))
        if standard_date_fields[0] < 1000 or standard_date_fields[0] > 2100:
            return db_str
        if len(standard_date_fields) > 1 and (standard_date_fields[1] > 12 or standard_date_fields[1] < 1):
            return db_str
        if len(standard_date_fields) > 2 and (standard_date_fields[2] > 31 or standard_date_fields[2] < 1):
            return db_str
        str_date_fields = [str(field) for field in standard_date_fields]
        form_date = unicode(self.default_form_separator.join(str_date_fields[::-1]))
        return form_date

class GeoCoverageType(object):
    @staticmethod
    def get_instance():
        if not hasattr(GeoCoverageType, 'instance'):
            GeoCoverageType.instance = GeoCoverageType.Singleton()
        return GeoCoverageType.instance

    class Singleton(object):
        def __init__(self):
            regions_str = region_options
            self.groupings = region_groupings
            self.regions = [(region_str, GeoCoverageType.munge(region_str)) for region_str in regions_str]
            self.regions_munged = [GeoCoverageType.munge(region_str) for region_str in regions_str]

        def munged_regions_to_printable_region_names(self, munged_regions):
            incl_regions = []
            for region_str, region_munged in self.regions:
                if region_munged in munged_regions:
                    incl_regions.append(region_str)
            for grouping_str, regions_str in self.groupings.items():
                all_regions_in = True
                for region_str in regions_str:
                    if region_str not in incl_regions:
                        all_regions_in = False
                        break
                if all_regions_in:
                    for region_str in regions_str:
                        incl_regions.remove(region_str)
                    incl_regions.append('%s (%s)' % (grouping_str, ', '.join(regions_str)))
            return ', '.join(incl_regions)

        def form_to_db(self, form_regions):
            assert isinstance(form_regions, list)
            coded_regions = u''
            for region_str, region_munged in self.regions:
                coded_regions += '1' if region_munged in form_regions else '0'
            regions_str = self.munged_regions_to_printable_region_names(form_regions)
            return '%s: %s' % (coded_regions, regions_str)

        def db_to_form(self, form_regions):
            '''
            @param form_regions e.g. 110000: England, Scotland
            @return e.g. ["england", "scotland"]
            '''
            regions = []
            if len(form_regions)>len(self.regions):
                for i, region in enumerate(self.regions):
                    region_str, region_munged = region
                    if form_regions[i] == '1':
                        regions.append(region_munged)
            return regions

    @staticmethod
    def munge(region):
        return region.lower().replace(' ', '_')

    def __getattr__(self, name):
        return getattr(self.instance, name)

def expand_abbreviations(dept):
    for brief_form in department_agency_abbreviations.keys():
        if brief_form in dept:
            dept = dept.replace(brief_form,
                                department_agency_abbreviations[brief_form])
    return dept
