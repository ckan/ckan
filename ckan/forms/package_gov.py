import formalchemy
from formalchemy import helpers as h
from sqlalchemy.util import OrderedDict
from pylons.i18n import _, ungettext, N_, gettext

from ckan.lib.helpers import literal
import common
import ckan.model as model
import package as package
from ckan.lib import schema_gov
from ckan.lib import field_types

__all__ = ['get_gov_fieldset']


class GeoCoverageExtraField(common.ConfiguredField):
    def get_configured(self):
        return self.GeoCoverageField(self.name).with_renderer(self.GeoCoverageRenderer)

    class GeoCoverageField(formalchemy.Field):
        def sync(self):
            if not self.is_readonly():
                pkg = self.model
                form_regions = self._deserialize() or []
                regions_db = schema_gov.GeoCoverageType.get_instance().form_to_db(form_regions)
                pkg.extras[self.name] = regions_db

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
                if self.params.get(self.name + '-' + region, u'') == u'True':
                    covered_regions.append(region)
            return covered_regions

        def deserialize(self):
            return self._serialized_value()

class SuggestTagRenderer(common.TagField.TagEditRenderer):
    def render(self, **kwargs):
        fs = self.field.parent
        pkg_dict = {}
        for field_name, field in fs.render_fields.items():
            pkg_dict[field_name] = field.renderer._value
        tag_suggestions = schema_gov.suggest_tags(pkg_dict)
        html = literal("<div>Suggestions (preview refreshes): %s</div>") % ' '.join(tag_suggestions)
        html += common.TagField.TagEditRenderer.render(self, **kwargs)
        return html
        

# Setup the fieldset
def build_package_gov_form(is_admin=False):
    builder = package.build_package_form()

    # Extra fields
    builder.add_field(common.TextExtraField('external_reference'))
    builder.add_field(common.DateExtraField('date_released'))
    builder.add_field(common.DateExtraField('date_updated'))
    builder.add_field(common.TextExtraField('update_frequency'))
    builder.add_field(common.SuggestedTextExtraField('geographic_granularity', options=schema_gov.geographic_granularity_options))
    builder.add_field(GeoCoverageExtraField('geographic_coverage'))
    builder.add_field(common.SuggestedTextExtraField('temporal_granularity', options=schema_gov.temporal_granularity_options))
    builder.add_field(common.DateRangeExtraField('temporal_coverage'))
    builder.add_field(common.SuggestedTextExtraField('categories', options=schema_gov.category_options))
    builder.add_field(common.CheckboxExtraField('national_statistic'))
    builder.add_field(common.TextExtraField('precision'))
    builder.add_field(common.SuggestedTextExtraField('department', options=schema_gov.government_depts))
    builder.add_field(common.TextExtraField('agency'))
    builder.add_field(common.TextExtraField('taxonomy_url'))

    # Labels and instructions
    builder.set_field_text('national_statistic', _('National Statistic'))

    # Options/settings
    builder.set_field_option('tags', 'with_renderer', SuggestTagRenderer)
    
    # Layout
    field_groups = OrderedDict([
        (_('Basic information'), ['name', 'title', 'external_reference',
                                  'notes']),
        (_('Details'), ['date_released', 'date_updated', 'update_frequency',
                        'geographic_granularity', 'geographic_coverage',
                        'temporal_granularity', 'temporal_coverage',
                        'categories', 'national_statistic', 'precision',
                        'url',]),
        (_('Resources'), ['resources']),
        (_('More details'), ['taxonomy_url', 'department', 'agency',
                             'author', 'author_email',
                             'maintainer', 'maintainer_email',
                             'license_id', 'tags' ]),
        ])
    if is_admin:
        field_groups['More details'].append('state')
    builder.set_displayed_fields(field_groups)
    return builder
    # Strings for i18n:
    [_('External reference'),  _('Date released'), _('Date updated'),
     _('Update frequency'), _('Geographic granularity'),
     _('Geographic coverage'), _('Temporal granularity'),
     _('Temporal coverage'), _('Categories'), _('National Statistic'),
     _('Precision'), _('Taxonomy URL'), _('Department'), _('Agency'), 
     ]

fieldsets = {} # fieldset cache

def get_gov_fieldset(is_admin=False):
    '''Returns the standard fieldset
    '''
    if not fieldsets:
        # fill cache
        fieldsets['package_gov_fs'] = build_package_gov_form().get_fieldset()
        fieldsets['package_gov_fs_admin'] = build_package_gov_form(is_admin=True).get_fieldset()

    if is_admin:
        fs = fieldsets['package_gov_fs_admin']
    else:
        fs = fieldsets['package_gov_fs']
    return fs
