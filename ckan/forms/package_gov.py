import re

import formalchemy
from formalchemy import helpers as h

import common
import ckan.model as model
import ckan.lib.helpers
import package as package

__all__ = ['package_gov_fs', 'package_gov_fs_admin', 'DateType', 'SelectRenderer']
government_depts = """
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
        err_str = 'Date must be format DD/MM/YYYY.'
        match = self.date_match.match(form_str)
        if not match:
            raise TypeError(err_str)
        matched_date = ''.join([group if group else '' for group in match.groups()])
        if matched_date != form_str:
            raise TypeError('%s Matched only "%s"' % (err_str, matched_date))
        standard_date_fields = [] # integers, year first
        for match_group in match.groups()[::-1]:
            if match_group is not None:
                standard_date_fields.append(int(match_group.strip('/-.')))
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

class DateField(formalchemy.Field):
    def sync(self):
        if not self.is_readonly():
            pkg = self.model
            form_date = self._deserialize()
            date_db = DateType.form_to_db(form_date)
            pkg.extras[self.name] = date_db

class TemporalCoverageField(formalchemy.Field):
    def sync(self):
        if not self.is_readonly():
            pkg = self.model
            vals = self._deserialize() or u''
            pkg.extras[self.name + '-from'] = DateType.form_to_db(vals[0])
            pkg.extras[self.name + '-to'] = DateType.form_to_db(vals[1])

class GeoCoverageType(object):
    @staticmethod
    def get_instance():
        if not hasattr(GeoCoverageType, 'instance'):
            GeoCoverageType.instance = GeoCoverageType.Singleton()
        return GeoCoverageType.instance

    class Singleton(object):
        def __init__(self):
            regions_str = ('England', 'Scotland', 'Wales', 'Northern Ireland', 'Overseas', 'Global')
            self.groupings = {'United Kingdom':['England', 'Scotland', 'Wales', 'Northern Ireland'], 'Great Britain':['England', 'Scotland', 'Wales']}
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
                    if GeoCoverageType.munge(region_str) not in incl_regions:
                        all_regions_in = False
                        break
                if all_regions_in:
                    for region_str in regions_str:
                        incl_regions.remove(GeoCoverageType.munge(region_str))
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


class GeoCoverageField(formalchemy.Field):
    def sync(self):
        if not self.is_readonly():
            pkg = self.model
            form_regions = self._deserialize() or []
            regions_db = GeoCoverageType.get_instance().form_to_db(form_regions)
            pkg.extras[self.name] = regions_db

class ExtraField(formalchemy.Field):
    def sync(self):
        if not self.is_readonly():
            pkg = self.model
            val = self._deserialize() or u''
            pkg.extras[self.name] = val


class ExtraTextRenderer(formalchemy.fields.TextFieldRenderer):
    def _get_value(self):
#        extras = self.field.parent._extras.value
#        if extras is None:
        extras = self.field.parent.model.extras # db
        return self._value or extras.get(self.field.name, u'') or u''

    def render(self, **kwargs):
        value = self._get_value()
        kwargs['size'] = '40'
        return h.text_field(self.name, value=value, maxlength=self.length, **kwargs)

    def render_readonly(self, **kwargs):
        return common.field_readonly_renderer(self.field.key, self._get_value())

class ExtraCheckboxRenderer(formalchemy.fields.CheckBoxFieldRenderer):
    def _get_value(self):
#        extras = self.field.parent._extras.value
#        if extras is None:
        extras = self.field.parent.model.extras
        return bool(self._value or extras.get(self.field.name))

    def render(self, **kwargs):
        value = self._get_value()
        kwargs['size'] = '40'
        return h.check_box(self.name, True, checked=value, **kwargs)
        return h.text_field(self.name, value=value, maxlength=self.length, **kwargs)

    def render_readonly(self, **kwargs):
        value = u'Yes' if self._get_value() else u'No'
        return common.field_readonly_renderer(self.field.key, value)

    def _serialized_value(self):
        # interpret params like this:
        # 'Package--some_field', u'True'
        param_val = self._params.get(self.name, u'')
        val = param_val == 'True'
        return val

    def deserialize(self):
        return u'Yes' if self._serialized_value() else u'No'


class GeoCoverageRenderer(formalchemy.fields.FieldRenderer):
    def _get_value(self):
        form_regions = self._value # params
        if not form_regions:
            extras = self.field.parent.model.extras # db
            db_regions = extras.get(self.field.name, []) or []
            form_regions = GeoCoverageType.get_instance().db_to_form(db_regions)
        return form_regions

    def render(self, **kwargs):
        value = self._get_value()
        kwargs['size'] = '40'
        html = u''
        for i, region in enumerate(GeoCoverageType.get_instance().regions):
            region_str, region_munged = region
            id = '%s-%s' % (self.name, region_munged)
            checked = region_munged in value
            cb = h.check_box(id, True, checked=checked, **kwargs)
            html += '<label for="%s">%s %s</label>' % (id, cb, region_str)
        return html

    def render_readonly(self, **kwargs):
        munged_regions = self._get_value()
        printable_region_names = GeoCoverageType.get_instance().munged_regions_to_printable_region_names(munged_regions)
        return common.field_readonly_renderer(self.field.key, printable_region_names)

    def _serialized_value(self):
        # interpret params like this:
        # 'Package--geographic_coverage-wales', u'True'
        # return list of covered regions
        covered_regions = []
        for region in GeoCoverageType.get_instance().regions_munged:
            if self._params.get(self.name + '-' + region, u'') == u'True':
                covered_regions.append(region)
        return covered_regions

    def deserialize(self):
        return self._serialized_value()

class ExtraDateRenderer(ExtraTextRenderer):
    def _get_value(self):
        form_date = ExtraTextRenderer._get_value(self)
        return DateType.db_to_form(form_date)

    def render_readonly(self, **kwargs):
        return common.field_readonly_renderer(self.field.key, self._get_value())

class TemporalCoverageRenderer(formalchemy.fields.FieldRenderer):
    def _get_value(self):
#        extras = self.field.parent._extras.value
#        if extras is None:
        extras = self.field.parent.model.extras
        if self._value:
            from_form, to_form = self._value
        else:
            from_ = extras.get(self.field.name + '-from') or u''
            to = extras.get(self.field.name + '-to') or u''
            from_form = DateType.db_to_form(from_)
            to_form = DateType.db_to_form(to)
        return (from_form, to_form)

    def render(self, **kwargs):
        from_, to = self._get_value()
        from_html = h.text_field(self.name + '-from', value=from_, **kwargs)
        to_html = h.text_field(self.name + '-to', value=to, **kwargs)
        html = '%s - %s' % (from_html, to_html)
        return html

    def render_readonly(self, **kwargs):
        val = self._get_value()
        if not val:
            val = u'', u''
        from_, to = val
        if to:
            val_str = '%s - %s' % (from_, to)
        else:            
            val_str = '%s' % from_
        return common.field_readonly_renderer(self.field.key, val_str)

    def _serialized_value(self):
        # interpret params like this:
        # 'Package--temporal_coverage-from', u'4/12/2009'
        param_val_from = self._params.get(self.name + '-from', u'')
        param_val_to = self._params.get(self.name + '-to', u'')
        return param_val_from, param_val_to

    def deserialize(self):
        return self._serialized_value()

class SelectRenderer(formalchemy.fields.FieldRenderer):
    def _get_value(self, **kwargs):
        extras = self.field.parent.model.extras
        return unicode(kwargs.get('selected', '') or self._value or extras.get(self.field.name, ''))

    def render(self, **kwargs):
        selected = self._get_value()
        options = [('', None)] + self.get_options() + [('other - please specify', 'other')]
        if selected in options:
            select_field_selected = selected
            text_field_value = u''
        elif selected:
            select_field_selected = u'other'
            text_field_value = selected or u''
        else:
            select_field_selected = u''
            text_field_value = u''            
        html = h.select(self.name, h.options_for_select(options, selected=select_field_selected, **kwargs))
        html += '<span class="margin">Other: %s</span>' % h.text_field(self.name+'-other', value=text_field_value, **kwargs)
        return html

    def render_readonly(self, **kwargs):
        return common.field_readonly_renderer(self.field.key, self._get_value())

    def _serialized_value(self):
        main_value = self._params.get(self.name, u'')
        other_value = self._params.get(self.name + '-other', u'')
        return other_value if main_value in ('', 'other') else main_value
        

class DepartmentRenderer(SelectRenderer):
    def get_options(self):
        if hasattr(self, 'options'):
            return self.options
        self.options = []
        for line in government_depts.split('\n'):
            if line:
                self.options.append(line.strip())
        return self.options

    def render_readonly(self, **kwargs):
        return common.field_readonly_renderer(self.field.key, self._get_value())

class GeoGranularityRenderer(SelectRenderer):
    def get_options(self):
        return ['national', 'regional', 'local authority', 'ward', 'point']

class TemporalGranularityRenderer(SelectRenderer):
    def get_options(self):
        return ['years', 'months', 'weeks', 'days', 'hours', 'points']

class CategoriesRenderer(SelectRenderer):
    def get_options(self):
        return ['Agriculture and Environment', 'Business and Energy', 'Children, Education and Skills', 'Crime and Justice', 'Economy', 'Government', 'Health and Social Care', 'Labour Market', 'People and Places', 'Population', 'Travel and Transport', 'Equality and Diversity', 'Migration']


# Setup the fieldset
package_gov_fs = package.PackageFieldSet()
package_gov_fs_admin = package.PackageFieldSet()
for fs in [package_gov_fs, package_gov_fs_admin]:
    for field in package.get_additional_package_fields():
        if field.name != 'extras':
            fs.append(field)
    fs.append(ExtraField('external_reference').with_renderer(ExtraTextRenderer))
    fs.append(DateField('date_released').with_renderer(ExtraDateRenderer).validate(DateType.form_validator))
    fs.append(DateField('date_updated').with_renderer(ExtraDateRenderer).validate(DateType.form_validator))
    fs.append(ExtraField('update_frequency').with_renderer(ExtraTextRenderer))
    fs.append(ExtraField('geographic_granularity').with_renderer(GeoGranularityRenderer))
    fs.append(GeoCoverageField('geographic_coverage').with_renderer(GeoCoverageRenderer))
    fs.append(ExtraField('temporal_granularity').with_renderer(ExtraTextRenderer))
    fs.append(TemporalCoverageField('temporal_coverage').with_renderer(TemporalCoverageRenderer))
    fs.append(ExtraField('categories').with_renderer(CategoriesRenderer))
    fs.append(ExtraField('national_statistic').with_renderer(ExtraCheckboxRenderer))
    fs.append(ExtraField('precision').with_renderer(ExtraTextRenderer))
    fs.append(ExtraField('taxonomy_url').with_renderer(ExtraTextRenderer))
    fs.append(ExtraField('agency').with_renderer(ExtraTextRenderer))

    fs.append(ExtraField('department').with_renderer(DepartmentRenderer))
    options = package.get_package_fs_options(fs)
    include = [fs.name, fs.title, fs.external_reference, fs.notes, fs.date_released, fs.date_updated, fs.update_frequency, fs.geographic_granularity, fs.geographic_coverage, fs.temporal_granularity, fs.temporal_coverage, fs.categories, fs.national_statistic, fs.precision, fs.url, fs.resources, fs.taxonomy_url, fs.department, fs.agency, fs.author, fs.author_email, fs.maintainer, fs.maintainer_email, fs.license, fs.tags,  ]
    if fs != package_gov_fs:
        include.append(fs.state)
        options += [fs.state.with_renderer(package.StateRenderer)]
    fs.configure(options=options,
                 include=include)


