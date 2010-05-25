import re

from pylons import config
import formalchemy
from formalchemy import helpers as h
from pylons.i18n import _, ungettext, N_, gettext

from common import ResourcesField, TagField, ExtrasField, TextExtraField, \
     TextRangeExtraField, SuggestedTextExtraField, package_name_validator

from builder import FormBuilder
import ckan.model as model
import ckan.lib.helpers
from ckan.lib.helpers import literal
import package

__all__ = ['build_package_form', 'package_fs', 'package_fs_admin', 'get_ca_fieldset']

# Note: 'Statistics Canada' has been put in the list of ministries, even
#       though it is technically an agency. This is because it is SC is
#       particularly important for this database.

ministries = ['Agriculture and Agri-Food', 'Canadian Heritage', 'Citizenship and Immigration', 'Environment', 'Finance', 'Fisheries and Oceans', 'Foreign Affairs and International Trade', 'Health', 'Human Resources and Social Development', 'Indian and Northern Affairs', 'Industry', 'Intergovernmental Affairs', 'Justice', 'National Defence', 'Natural Resources', 'Public Safety', 'Public Works and Government Services', 'Statistics Canada', 'Transport', 'Veterans Affairs', 'Western Economic Diversification']

agencies = ['Air Transport Security Authority', 'Artists and Producers Professional Relations Tribunal', 'Atlantic Canada Opportunities Agency', 'Atlantic Pilotage Authority', 'Atomic Energy of Canada Limited', 'Auditor General', 'Bank of Canada', 'Border Services Agency', 'Business Development Bank of Canada', 'Business Service Centres', 'Canada Information Office', 'Canada Lands Company', 'Canada-Newfoundland Offshore Petroleum Board', 'Canada-Nova Scotia Offshore Petroleum Board', 'Canada Post Corporation', 'Canadian Broadcasting Corporation', 'Cape Breton Development Office', 'Centre for Occupational Health and Safety', 'Centre on Substance Abuse', 'Climate Change Secretariat', 'Commercial Corporation', 'Competition Bureau', 'Competition Tribunal', 'Copyright Board', 'Correctional Service', 'Council for the Arts', 'Courts Administration Service', 'Cultural Property Export Review Board', 'Dairy Commission', 'Defence Construction Canada', 'Defence Research and Development Canada', 'Deposit Insurance Corporation', 'Economic Development Agency for Quebec Regions', 'Elections Canada', 'Enterprise Cape Breton Corporation', 'Environment and Sustainable Development Commissioner', 'Environmental Assessment Agency', 'Environmental Protection Review Canada', 'Ethics Commissioner', 'Export Development Canada', 'Federal Bridge Corporation Limited', 'Federal Judicial Affairs Commissioner', 'Federal Science for Sustainable Development', 'Financial Consumer Agency', 'Firearms Centre', 'Food Inspection Agency', 'Freshwater Fish Marketing Corporation', 'Grain Commission', 'Human Rights Commission', 'Human Rights Tribunal', 'Industrial Relations Board', 'Institutes of Health Research', 'Intergovernmental Conference Secretariat', 'International Development Agency', 'International Trade Tribunal', 'Library and Archives Canada', 'Mortgage and Housing Corporation', 'National Capital Commission', 'National Film Board', 'National Parole Board', 'National Research Council', 'National Round Table on the Environment and the Economy', 'National Search and Rescue Secretariat', 'Natural Sciences and Engineering Research Council of Canada', 'Northern Pipeline Agency', 'Nuclear Safety Commission', 'Official Languages Commissioner', 'Pari-Mutuel Agency', 'Parks Canada', 'Pension Plan Investment Board', 'Polar Commission', 'Police College', 'Privacy Commissioner of Canada', 'Public Health Agency of Canada', 'Public Service Commission of Canada', 'Radio-Television and Telecommunications Commission', 'Revenue Agency', 'Review Tribunals Commissioner', 'Royal Canadian Mint', 'School of Public Service', 'Social Sciences and Humanities Research Council', 'Space Agency', 'Standards Council of Canada', 'Tourism Commission', 'Transportation Agency', 'Transportation Safety Board', 'Treasury Board Secretariat', 'VIA Rail Canada', 'Wheat Board']

def build_package_form(is_admin=False):
    builder = FormBuilder(model.Package)

    # Extra fields
    builder.add_field(ResourcesField('resources', hidden_label=True))
    builder.add_field(TagField('tags'))
    builder.add_field(TextExtraField('date_released', validate_re=('^\d{4}-\d{2}-\d{2}$', 'YYYY-MM-DD')))
    builder.add_field(TextExtraField('date_updated', validate_re=('^\d{4}-\d{2}-\d{2}$', 'YYYY-MM-DD')))
    builder.add_field(TextExtraField('update_frequency'))
    builder.add_field(TextRangeExtraField('temporal_coverage', validate_re=('^\d{4}$', 'YYYY')))
    builder.add_field(SuggestedTextExtraField('level_of_government', ['Federal', 'Provincial/Territorial', 'Regional', 'Municipal']))
    builder.add_field(SuggestedTextExtraField('department', ministries))
    builder.add_field(SuggestedTextExtraField('federal_agency', agencies))

    # Labels and instructions
    builder.set_field_text('name', '%s %s' % (_('Name'), _('(required)')), _("Insert a short, unique, descriptive title here, using only 'a-z', '0-9' and '-_'. Must be lowercase; no spaces allowed."), _('(Example: geogratis-radarsat-mosaic)'))
    builder.set_field_text('title', instructions=_('Insert a more descriptive title - ideally the same as that used on the government website.'), hints=_('(Example: RADARSAT Ortho-rectified Mosaic of Canada, Lambert Conformal Conic, 1000 Metres)'))
    builder.set_field_text('url', instructions=_('The link to the government web page where the data is described and located. Do not link to the dataset itself.'), hints=_('(Example: http://geogratis.cgdi.gc.ca/geogratis/en/collection/detail.do?id=9369)'))
    builder.set_field_text('resources', instructions=literal(_('<div>URL: The link to the actual data set (if available)</div><div>Format: Describe the format type, e.g. XML, CSV, SHAPE, etc.</div><div>Description: A description of the data. Feel free to copy the description on the government website.</div><div>Hash: Just leave it blank.</div>')))
    builder.set_field_text('date_released', instructions=_('Please enter in YYYY-MM-DD format.'), hints=_('(Example: 2009-01-15)'))
    builder.set_field_text('date_updated', instructions=_('Please enter in YYYY-MM-DD format.'), hints=_('(Example: 2010-04-12)'))
    builder.set_field_text('license_id', _('License'), instructions=_('Select the license type'))
    builder.set_field_text('update_frequency', instructions=_('Only if available'), hints=_('(Example: monthly)'))
    builder.set_field_text('temporal_coverage', _('Years covered'), instructions=_('Please enter in YYYY - YYYY format'), hints=_('(Example: 1992 - 1995)'))
    builder.set_field_text('tags', _('Tags'), instructions=_('Include tags you think are descriptive and appropriate. Tags are space separated; to  join two words together, use a dash (-) or underscore (_).'), hints=_('(Example:  radar radar-imagery radarsat-1 satellite-imagery mosaic  spectral-engineering geogratis canada gcmd earth-science)'))
    builder.set_field_text('notes', _('Notes'), instructions=_('A  more detailed description of the data can go here. Feel free to copy  & paste from the government website.'), hints=literal(_('You can use <a href="http://daringfireball.net/projects/markdown/syntax">Markdown formatting</a> here.')))
    builder.set_field_text('level_of_government', instructions=_('What level of government produced this data?'))
    builder.set_field_text('department', _('Federal Ministry (if applicable)'), instructions=_('Indicate the ministry responsible for the data.'))
    builder.set_field_text('federal_agency', instructions=_('Indicate the agency responsible for the data.'))
    builder.set_field_text('maintainer_email', instructions=_('Include an email address for the ministry or agency responsible for maintaining the data (if available).'))

    # Options/settings
    builder.set_field_option('name', 'validate', package_name_validator)
    builder.set_field_option('license_id', 'dropdown', {'options':[('', '')] + model.Package.get_license_options()})
    builder.set_field_option('state', 'dropdown', {'options':model.State.all})
    builder.set_field_option('notes', 'textarea', {'size':'60x15'})

    # Layout
    field_groups = {_('Basic information'):['name', 'title', 'url'],
                    _('Resources'):['resources'],
                    _('Detail'):['date_released', 'date_updated',
                                 'update_frequency', 'temporal_coverage',
                                 'license_id', 'notes', 'tags',
                                 'level_of_government', 'department',
                                 'federal_agency', 'maintainer_email',
                                 ]
                    }
    if is_admin:
        field_groups['Detail'].append('state')
    builder.set_displayed_fields(field_groups)
    builder.set_label_prettifier(package.prettify)
    return builder
    #i18n
    [_('Name'), _('Title'), _('URL'), _('Resources'), _('Date released'),
     _('Date updated'), _('Update frequency'), _('Years covered'),
     _('License'), _('Notes'), _('Tags'), _('Level of government'),
     _('Federal Ministry'), _('Federal Agency'), _('Maintainer email')]


package_fs = build_package_form().get_fieldset()
package_fs_admin = build_package_form(is_admin=True).get_fieldset()

def get_ca_fieldset(is_admin=False):
    if is_admin:
        return package_fs_admin
    else:
        return package_fs

