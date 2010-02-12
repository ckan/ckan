import formalchemy
from formalchemy import helpers as h

from ckan.lib.helpers import literal
import common
import ckan.model as model
import package as package
from ckan.lib import schema_gov

__all__ = ['package_gov_fs', 'package_gov_fs_admin', 'SelectRenderer']


class DateField(formalchemy.Field):
    def sync(self):
        if not self.is_readonly():
            pkg = self.model
            form_date = self._deserialize()
            date_db = schema_gov.DateType.form_to_db(form_date)
            pkg.extras[self.name] = date_db

class TemporalCoverageField(formalchemy.Field):
    def sync(self):
        if not self.is_readonly():
            pkg = self.model
            vals = self._deserialize() or u''
            pkg.extras[self.name + '-from'] = schema_gov.DateType.form_to_db(vals[0])
            pkg.extras[self.name + '-to'] = schema_gov.DateType.form_to_db(vals[1])



class GeoCoverageField(formalchemy.Field):
    def sync(self):
        if not self.is_readonly():
            pkg = self.model
            form_regions = self._deserialize() or []
            regions_db = schema_gov.GeoCoverageType.get_instance().form_to_db(form_regions)
            pkg.extras[self.name] = regions_db

class ExtraField(formalchemy.Field):
    def sync(self):
        if not self.is_readonly():
            pkg = self.model
            val = self._deserialize() or u''
            pkg.extras[self.name] = val

class SuggestTagRenderer(package.TagEditRenderer):
    def render(self, **kwargs):
        fs = self.field.parent
        pkg_dict = {}
        for field_name, field in fs.render_fields.items():
            pkg_dict[field_name] = field.renderer._value
        tag_suggestions = schema_gov.suggest_tags(pkg_dict)
        html = literal("<div>Suggestions (preview refreshes): %s</div>") % ' '.join(tag_suggestions)
        html += package.TagEditRenderer.render(self, **kwargs)
        return html

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
        extras = self.field.parent.model.extras
        return bool(self._value or extras.get(self.field.name) == u'yes')

    def render(self, **kwargs):
        value = self._get_value()
        kwargs['size'] = '40'
        return h.check_box(self.name, True, checked=value, **kwargs)
        return h.text_field(self.name, value=value, maxlength=self.length, **kwargs)

    def render_readonly(self, **kwargs):
        value = u'yes' if self._get_value() else u'no'
        return common.field_readonly_renderer(self.field.key, value)

    def _serialized_value(self):
        # interpret params like this:
        # 'Package--some_field', u'True'
        param_val = self._params.get(self.name, u'')
        val = param_val == 'True'
        return val

    def deserialize(self):
        return u'yes' if self._serialized_value() else u'no'


class GeoCoverageRenderer(formalchemy.fields.FieldRenderer):
    def _get_value(self):
        form_regions = self._value # params
        if not form_regions:
            extras = self.field.parent.model.extras # db
            db_regions = extras.get(self.field.name, []) or []
            form_regions = schema_gov.GeoCoverageType.get_instance().db_to_form(db_regions)
        return form_regions

    def render(self, **kwargs):
        value = self._get_value()
        kwargs['size'] = '40'
        html = u''
        for i, region in enumerate(schema_gov.GeoCoverageType.get_instance().regions):
            region_str, region_munged = region
            id = '%s-%s' % (self.name, region_munged)
            checked = region_munged in value
            cb = literal(h.check_box(id, True, checked=checked, **kwargs))
            html += literal('<label for="%s">%s %s</label>') % (id, cb, region_str)
        return html

    def render_readonly(self, **kwargs):
        munged_regions = self._get_value()
        printable_region_names = schema_gov.GeoCoverageType.get_instance().munged_regions_to_printable_region_names(munged_regions)
        return common.field_readonly_renderer(self.field.key, printable_region_names)

    def _serialized_value(self):
        # interpret params like this:
        # 'Package--geographic_coverage-wales', u'True'
        # return list of covered regions
        covered_regions = []
        for region in schema_gov.GeoCoverageType.get_instance().regions_munged:
            if self._params.get(self.name + '-' + region, u'') == u'True':
                covered_regions.append(region)
        return covered_regions

    def deserialize(self):
        return self._serialized_value()

class ExtraDateRenderer(ExtraTextRenderer):
    def _get_value(self):
        form_date = ExtraTextRenderer._get_value(self)
        return schema_gov.DateType.db_to_form(form_date)

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
            from_form = schema_gov.DateType.db_to_form(from_)
            to_form = schema_gov.DateType.db_to_form(to)
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
        html = literal(h.select(self.name, h.options_for_select(options, selected=select_field_selected, **kwargs)))
        other_name = self.name+'-other'
        html += literal('<label class="inline" for="%s">Other: %s</label>') % (other_name, literal(h.text_field(other_name, value=text_field_value, **kwargs)))
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
        self.options = schema_gov.government_depts
        return self.options

    def render_readonly(self, **kwargs):
        return common.field_readonly_renderer(self.field.key, self._get_value())

class GeoGranularityRenderer(SelectRenderer):
    def get_options(self):
        return schema_gov.geographic_granularity_options

class TemporalGranularityRenderer(SelectRenderer):
    def get_options(self):
        return schema_gov.temporal_granularity_options

class CategoriesRenderer(SelectRenderer):
    def get_options(self):
        return schema_gov.category_options


# Setup the fieldset
package_gov_fs = package.PackageFieldSet()
package_gov_fs_admin = package.PackageFieldSet()
for fs in [package_gov_fs, package_gov_fs_admin]:
    for field in package.get_additional_package_fields():
        if field.name != 'extras':
            fs.append(field)
    fs.append(ExtraField('external_reference').with_renderer(ExtraTextRenderer))
    fs.append(DateField('date_released').with_renderer(ExtraDateRenderer).validate(schema_gov.DateType.form_validator))
    fs.append(DateField('date_updated').with_renderer(ExtraDateRenderer).validate(schema_gov.DateType.form_validator))
    fs.append(ExtraField('update_frequency').with_renderer(ExtraTextRenderer))
    fs.append(ExtraField('geographic_granularity').with_renderer(GeoGranularityRenderer))
    fs.append(GeoCoverageField('geographic_coverage').with_renderer(GeoCoverageRenderer))
    fs.append(ExtraField('temporal_granularity').with_renderer(TemporalGranularityRenderer))
    fs.append(TemporalCoverageField('temporal_coverage').with_renderer(TemporalCoverageRenderer))
    fs.append(ExtraField('categories').with_renderer(CategoriesRenderer))
    fs.append(ExtraField('national_statistic').with_renderer(ExtraCheckboxRenderer))
    fs.append(ExtraField('precision').with_renderer(ExtraTextRenderer))
    fs.append(ExtraField('taxonomy_url').with_renderer(ExtraTextRenderer))
    fs.append(ExtraField('department').with_renderer(DepartmentRenderer))
    fs.append(ExtraField('agency').with_renderer(ExtraTextRenderer))

    options = package.get_package_fs_options(fs)
    include = [fs.name, fs.title, fs.external_reference, fs.notes, fs.date_released, fs.date_updated, fs.update_frequency, fs.geographic_granularity, fs.geographic_coverage, fs.temporal_granularity, fs.temporal_coverage, fs.categories, fs.national_statistic, fs.precision, fs.url, fs.resources, fs.taxonomy_url, fs.department, fs.agency, fs.author, fs.author_email, fs.maintainer, fs.maintainer_email, fs.license, fs.tags,  ]
    options += [fs.tags.with_renderer(SuggestTagRenderer)]
    if fs != package_gov_fs:
        include.append(fs.state)
        options += [fs.state.with_renderer(package.StateRenderer)]
    fs.configure(options=options,
                 include=include)


