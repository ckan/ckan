import re

from pylons import config
import formalchemy
from formalchemy import helpers as h

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
    builder.add_field(SuggestedTextExtraField('federal_ministry', ministries))
    builder.add_field(SuggestedTextExtraField('federal_agency', agencies))

    # Labels and instructions
    builder.set_field_text('name', 'Name (required)', "Insert a short, unique, descriptive title here, using only 'a-z', '0-9' and '-_'. Must be lowercase; no spaces allowed.", '(Example: geogratis-radarsat-mosaic)')
    builder.set_field_text('title', instructions='Insert a more descriptive title - ideally the same as that used on the government website.', hints='(Example: RADARSAT Ortho-rectified Mosaic of Canada, Lambert Conformal Conic, 1000 Metres)')
    builder.set_field_text('url', instructions='The link to the government web page where the data is described and located. Do not link to the dataset itself.', hints='(Example: http://geogratis.cgdi.gc.ca/geogratis/en/collection/detail.do?id=9369)')
    builder.set_field_text('resources', instructions=literal('<div>URL: The link to the actual data set (if available)</div><div>Format: Describe the format type, e.g. XML, CSV, SHAPE, etc.</div><div>Description: A description of the data. Feel free to copy the description on the government website.</div><div>Hash: Just leave it blank.</div>'))
    builder.set_field_text('date_released', instructions='Please enter in YYYY-MM-DD format.', hints='(Example: 2009-01-15)')
    builder.set_field_text('date_updated', instructions='Please enter in YYYY-MM-DD format.', hints='(Example: 2010-04-12)')
    builder.set_field_text('license_id', 'License', instructions='Select the license type')
    builder.set_field_text('update_frequency', instructions='Only if available', hints='(Example: monthly)')
    builder.set_field_text('temporal_coverage', 'Years covered', instructions='Please enter in YYYY - YYYY format', hints='(Example: 1992 - 1995)')
    builder.set_field_text('tags', 'Tags', instructions='Include tags you think are descriptive and appropriate. Tags are space separated; to  join two words together, use a dash (-) or underscore (_).', hints='(Example:  radar radar-imagery radarsat-1 satellite-imagery mosaic  spectral-engineering geogratis canada gcmd earth-science)')
    builder.set_field_text('notes', 'Notes', instructions='A  more detailed description of the data can go here. Feel free to copy  & paste from the government website.', hints=literal('You can use <a href="http://daringfireball.net/projects/markdown/syntax">Markdown formatting</a> here.'))
    builder.set_field_text('level_of_government', instructions='What level of government produced this data?')
    builder.set_field_text('federal_ministry', 'Federal Ministry (if applicable)', instructions='Indicate the ministry responsible for the data.')
    builder.set_field_text('federal_agency', instructions='Indicate the agency responsible for the data.')
    builder.set_field_text('maintainer_email', instructions='Include an email address for the ministry or agency responsible for maintaining the data (if available).')

    # Options/settings
    builder.set_field_option('name', 'validate', package_name_validator)
    builder.set_field_option('license_id', 'dropdown', {'options':[('', None)] + model.Package.get_license_options()})
    builder.set_field_option('state', 'dropdown', {'options':model.State.all})
    builder.set_field_option('notes', 'textarea', {'size':'60x15'})

    # Layout
    field_groups = {'Basic information':['name', 'title', 'url'],
                    'Resources':['resources'],
                    'Detail':['date_released', 'date_updated',
                              'update_frequency', 'temporal_coverage',
                              'license_id', 'notes', 'tags',
                              'level_of_government', 'federal_ministry',
                              'federal_agency', 'maintainer_email',
                              ]
                    }
    if is_admin:
        field_groups['Detail'].append('state')
    builder.set_displayed_fields_in_groups(field_groups)
    builder.set_label_prettifier(package.prettify)
    builder.set_form_template('package/form')
    return builder

package_fs = build_package_form().get_fieldset()
package_fs_admin = build_package_form(is_admin=True).get_fieldset()

def get_ca_fieldset(is_admin=False):
    if is_admin:
        return package_fs_admin
    else:
        return package_fs

