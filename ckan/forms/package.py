import re

from pylons import config
import formalchemy
from formalchemy import helpers as h
from sqlalchemy.util import OrderedDict

from common import ResourcesField, TagField, ExtrasField, package_name_validator
from builder import FormBuilder
import ckan.model as model
import ckan.lib.helpers
from ckan.lib.helpers import literal

__all__ = ['prettify', 'build_package_form', 'package_fs', 'package_fs_admin', 'get_standard_fieldset']


def prettify(field_name):
    field_name = re.sub('(?<!\w)[Uu]rl(?!\w)', 'URL', field_name.replace('_', ' ').capitalize())
    return field_name.replace('_', ' ')

def build_package_form(is_admin=False):
    builder = FormBuilder(model.Package)

    # Extra fields
    builder.add_field(ResourcesField('resources', hidden_label=True))
    builder.add_field(TagField('tags'))
    builder.add_field(ExtrasField('extras', hidden_label=True))

    # Labels and instructions
    builder.set_field_text('name', 'Name (required)', hints=literal("<strong>Unique identifier</strong> for package.<br/>2+ chars, lowercase, using only 'a-z0-9' and '-_'"))
    builder.set_field_text('license_id', 'License')
    builder.set_field_text('tags', 'Tags', '(space separated list)')
    builder.set_field_text('notes', 'Notes', hints=literal('You can use <a href="http://daringfireball.net/projects/markdown/syntax">Markdown formatting</a> here.'))

    # Options/settings
    builder.set_field_option('name', 'validate', package_name_validator)
    builder.set_field_option('license_id', 'dropdown', {'options':[('', None)] + model.Package.get_license_options()})
    builder.set_field_option('state', 'dropdown', {'options':model.State.all})
    builder.set_field_option('notes', 'textarea', {'size':'60x15'})

    # Layout
    field_groups = OrderedDict([
        ('Basic information', ['name', 'title', 'version', 'url',
                               'notes']),
        ('Resources', ['resources']),
        ('Detail', ['author', 'author_email',
                    'maintainer', 'maintainer_email',
                    'license_id', 'tags']),
        ('Extras', ['extras']),
        ])
    if is_admin:
        field_groups['Detail'].append('state')
    builder.set_displayed_fields(field_groups)
    builder.set_label_prettifier(prettify)
    return builder

package_fs = build_package_form().get_fieldset()
package_fs_admin = build_package_form(is_admin=True).get_fieldset()

def get_standard_fieldset(is_admin=False):
    '''Returns the standard fieldset
    '''
    if is_admin:
        return package_fs_admin
    else:
        return package_fs
