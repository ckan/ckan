import re

from pylons import config
import formalchemy
from formalchemy import helpers as h
from sqlalchemy.util import OrderedDict
from pylons.i18n import _, ungettext, N_, gettext

from common import ResourcesField, TagField, ExtrasField, package_name_validator
from builder import FormBuilder
import ckan.model as model
import ckan.lib.helpers
from ckan.lib.helpers import literal

__all__ = ['prettify', 'build_package_form', 'get_standard_fieldset']


def prettify(field_name):
    field_name = re.sub('(?<!\w)[Uu]rl(?!\w)', 'URL', field_name.replace('_', ' ').capitalize())
    return _(field_name.replace('_', ' '))

def build_package_form(is_admin=False):
    builder = FormBuilder(model.Package)

    # Extra fields
    builder.add_field(ResourcesField('resources', hidden_label=True))
    builder.add_field(TagField('tags'))
    builder.add_field(ExtrasField('extras', hidden_label=True))

    # Labels and instructions
    builder.set_field_text('name', '%s %s' % (_('Name'), _('(required)')), hints=literal(_("<strong>Unique identifier</strong> for package.<br/>2+ chars, lowercase, using only 'a-z0-9' and '-_'")))
    builder.set_field_text('license_id', _('License'))
    builder.set_field_text('tags', _('Tags'), _('(space separated list)'))
    builder.set_field_text('notes', _('Notes'), hints=literal(_('You can use <a href="http://daringfireball.net/projects/markdown/syntax">Markdown formatting</a> here.')))

    # Options/settings
    builder.set_field_option('name', 'validate', package_name_validator)
    builder.set_field_option('license_id', 'dropdown', {'options':[('', None)] + model.Package.get_license_options()})
    builder.set_field_option('state', 'dropdown', {'options':model.State.all})
    builder.set_field_option('notes', 'textarea', {'size':'60x15'})

    # Layout
    field_groups = OrderedDict([
        (_('Basic information'), ['name', 'title', 'version', 'url',
                               'notes', 'tags']),
        (_('Resources'), ['resources']),
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
    [_('Name'),  _('Title'), _('Version'), _('URL'),
     _('Notes'), _('Resources'), _('Author'), _('Author email'), _('Maintainer'),
     _('Maintainer email'), _('License'), _('Tags'), _('Extras'), _('State')]

def get_standard_fieldset(is_admin=False):
    '''Returns the package fieldset (optionally with admin fields)'''

    return build_package_form(is_admin=is_admin).get_fieldset()
