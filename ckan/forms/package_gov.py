import re

import formalchemy
from formalchemy import helpers as h

import common
import ckan.model as model
import ckan.lib.helpers
import package as package

__all__ = ['package_gov_fs', 'package_gov_fs_admin', 'DateType']
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
        extras = self.field.parent.model.extras
        return self._value or extras.get(self.field.name, u'') or u''

    def render(self, **kwargs):
        value = self._get_value()
        kwargs['size'] = '40'
        return h.text_field(self.name, value=value, maxlength=self.length, **kwargs)

    def render_readonly(self, **kwargs):
        return common.field_readonly_renderer(self.field.key, self._get_value())

class DateRenderer(ExtraTextRenderer):
    def _get_value(self):
        form_date = ExtraTextRenderer._get_value(self)
        return DateType.db_to_form(form_date)

    def render_readonly(self, **kwargs):
        return common.field_readonly_renderer(self.field.key, self._get_value())

class SelectRenderer(formalchemy.fields.FieldRenderer):
    def _get_value(self, **kwargs):
##        extras = self.field.parent._extras.value
##        if extras is None:
        extras = self.field.parent.model.extras
        return unicode(kwargs.get('selected', '') or self._value or extras.get(self.field.name, '')) 

    def render(self, **kwargs):
        selected = self._get_value()
        options = [('', None)] + self.get_options() + [('Other - please specify', 'other')]
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
        return common.field_readonly_renderer(self.field.name, self._get_value())

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

# Setup the fieldset
package_gov_fs = package.PackageFieldSet()
package_gov_fs_admin = package.PackageFieldSet()
for fs in [package_gov_fs, package_gov_fs_admin]:
    for field in package.get_additional_package_fields():
        if field.name != 'extras':
            fs.append(field)
    fs.append(ExtraField('external_reference').with_renderer(ExtraTextRenderer))
    fs.append(ExtraField('department').with_renderer(DepartmentRenderer))
    fs.append(DateField('date_released').with_renderer(DateRenderer).validate(DateType.form_validator))
    options = package.get_package_fs_options(fs)
    include = [fs.name, fs.title, fs.external_reference, fs.notes, fs.date_released, fs.url, fs.resources, fs.author, fs.author_email, fs.maintainer, fs.maintainer_email, fs.department, fs.license, fs.tags,  ]
    if fs != package_gov_fs:
        include.append(fs.state)
        options += [fs.state.with_renderer(package.StateRenderer)]
    fs.configure(options=options,
                 include=include)


