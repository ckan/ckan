import re

from pylons import config
import formalchemy
from formalchemy import helpers as h
from sqlalchemy.util import OrderedDict
from pylons.i18n import _, ungettext, N_, gettext

from common import ResourcesField, TagField, ExtrasField, GroupSelectField, package_name_validator
from builder import FormBuilder
import ckan.model as model
import ckan.lib.helpers
from ckan.lib.helpers import literal

__all__ = ['prettify', 'build_package_form', 'get_standard_fieldset']


def prettify(field_name):
    field_name = re.sub('(?<!\w)[Uu]rl(?!\w)', 'URL', field_name.replace('_', ' ').capitalize())
    return _(field_name.replace('_', ' '))

def build_package_form(is_admin=False, user_editable_groups=None, **params):
    builder = FormBuilder(model.Package)

    # Extra fields
    builder.add_field(GroupSelectField('groups', allow_empty=True, user_editable_groups=user_editable_groups))
    builder.add_field(ResourcesField('resources', hidden_label=True))
    builder.add_field(TagField('tags'))
    builder.add_field(ExtrasField('extras', hidden_label=True))

    # Labels and instructions
    builder.set_field_text(
        'title',
        instructions='The title of the data set.',
        further_instructions='Use a short descriptive title for the data set. It should not be a description though - save that for the Notes field. Do not give a trailing full stop.',
    )
    builder.set_field_text(
        'name', 
        '%s %s' % (
            _('Name'),
            _('(required)')
        ), 
        hints=literal(_("<strong>Unique identifier</strong> for package.<br/>2+ chars, lowercase, using only 'a-z0-9' and '-_'"))
    )
    builder.set_field_text(
        'version',
        instructions='A number representing the version (if applicable) e.g. 1.2.0',
    )
    builder.set_field_text(
        'url',
        instructions='This is usually the URL for the package project home page not the data itself.',
        hints='e.g. http://www.example.com/growth-figures.html',
    )
    builder.set_field_text(
        'author',
        instructions='The permanent contact name for enquiries about this particular dataset.',
    )
    builder.set_field_text(
        'author_email',
    )
    builder.set_field_text(
        'license_id',
        _('License'),
        instructions='The licence under which the dataset is released.',
    )
    builder.set_field_text(
        'tags', 
        _('Tags'), 
        _('(space separated list)')
    )
    builder.set_field_text(
        'resources',
        instructions='The files containing the data or address of the APIs for accessing it.',
        further_instructions=literal('<br />These can be repeated as required. For example if the data is being supplied in multiple formats, or split into different areas or time periods, each file is a different \'resource\' which should be described differently. They will all appear on the dataset page on CKAN together.<br /><br /> <b>URL:</b> This is the Internet link directly to the data - by selecting this link in a web browser, the user will immediately download the full data set. Note that datasets are not hosted on this site, but by the publisher of the data. Alternatively the URL can point to an API server such as a SPARQL endpoint or JSON-P service.<br /> <b>Format:</b> This should give the file format in which the data is supplied. <br /><b>Description</b> Any information you want to add to describe the resource.<br />'),  
        hints='Format choices: CSV | RDF | XML | XBRL | SDMX | HTML+RDFa | Other as appropriate'
    )
    builder.set_field_text(
        'notes', 
        _('Notes'), 
        instructions='The main description of the dataset',
        further_instructions='It is often displayed with the package title. In particular, it should start with a short sentence that describes the data set succinctly, because the first few words alone may be used in some views of the data sets.',
        hints=literal(_('You can use <a href="http://daringfireball.net/projects/markdown/syntax">Markdown formatting</a> here.'))
    )

    # Options/settings
    builder.set_field_option('name', 'validate', package_name_validator)
    builder.set_field_option('license_id', 'dropdown', {'options':[('', None)] + model.Package.get_license_options()})
    builder.set_field_option('state', 'dropdown', {'options':model.State.all})
    builder.set_field_option('notes', 'textarea', {'size':'60x15'})

    # Layout
    field_groups = OrderedDict([
        (_('Basic information'), ['title', 'name', 'version', 'url',
                               'notes', 'tags']),
        (_('Resources'), ['resources']),
        (_('Groups'), ['groups']),
        (_('Detail'), ['author', 'author_email',
                    'maintainer', 'maintainer_email',
                    'license_id']),
        (_('Extras'), ['extras']),
        ])
    if is_admin:
        field_groups[_('Detail')].append('state')
    builder.set_displayed_fields(field_groups)
    builder.set_label_prettifier(prettify)
    return builder
    # Strings for i18n:
    [ _('Title'), _('Name'), _('Version'), _('URL'),
     _('Notes'), _('Resources'), _('Author'), _('Author email'), _('Maintainer'),
     _('Maintainer email'), _('License'), _('Tags'), _('Extras'), _('State')]

def get_standard_fieldset(is_admin=False, user_editable_groups=None, **kwargs):
    '''Returns the package fieldset (optionally with admin fields)'''

    return build_package_form(is_admin=is_admin, user_editable_groups=user_editable_groups).get_fieldset()
