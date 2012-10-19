import formalchemy
from formalchemy import helpers as fa_h
import ckan.lib.helpers as h
from pylons.i18n import _, ungettext, N_, gettext

from builder import FormBuilder
from sqlalchemy.util import OrderedDict
import ckan.model as model
import common
from common import ExtrasField, PackageNameField
from ckan.lib.helpers import literal

__all__ = ['get_group_dict', 'edit_group_dict']

# for group_fs_combined (REST)
class PackagesField(common.ConfiguredField):
    def get_configured(self):
        return self.PackagesField(self.name).with_renderer(self.PackageEditRenderer)

    class PackagesField(formalchemy.Field):
        def sync(self):
            if not self.is_readonly():
                self._update_packages()

        def _update_packages(self):
            group = self.model
            packages = self._deserialize()
            group.packages = packages

    class PackageEditRenderer(formalchemy.fields.FieldRenderer):
        def deserialize(self):
            value = self.params[self.name]
            if isinstance(value, list): # from rest i/f
                pkg_list = value
            elif isinstance(value, (unicode, str)): # from form
                packages_as_string = unicode(value)
                packages_as_string = packages_as_string.replace(',', ' ')
                pkg_list = packages_as_string.split()
            packages = [model.Package.get(pkg_ref) for pkg_ref in pkg_list]
            return packages        

# For new_package_group_fs
class PackagesRenderer(formalchemy.fields.FieldRenderer):
    def render(self, **kwargs):
        kwargs['class'] = 'autocomplete'
        kwargs['data-autocomplete-url'] = h.url_for(controller='package', action='autocomplete', id=None)
        html = fa_h.text_field(self.name, **kwargs)
        return html

def build_group_form(is_admin=False, with_packages=False):
    builder = FormBuilder(model.Group)
    builder.set_field_text('name', _('Name'), literal("<strong>Unique identifier</strong> for group.<br/>2+ chars, lowercase, using only 'a-z0-9' and '-_'<p></p>"))
    builder.set_field_option('name', 'validate', common.group_name_validator)
    builder.set_field_option('description', 'textarea', {'size':'60x15'})
    builder.add_field(ExtrasField('extras', hidden_label=True))
    displayed_fields = ['name', 'title', 'description']
    if is_admin: 
        builder.set_field_option('state', 'dropdown', {'options':model.State.all})
        displayed_fields.append('state')
    if with_packages:
        builder.add_field(PackagesField('packages'))
        displayed_fields.append('packages')
    builder.set_displayed_fields(OrderedDict([(_('Details'), displayed_fields),
                                              (_('Extras'), ['extras'])]))
    builder.set_label_prettifier(common.prettify)
    return builder  

fieldsets = {}

def get_group_fieldset(combined=False, is_admin=False):
    fs_name = 'group_fs'
    if is_admin:
        fs_name += '_admin'
    if combined:
        fs_name += '_combined'
    if not fs_name in fieldsets:
        # group_fs has no packages - first half of the WUI form
        fieldsets[fs_name] = build_group_form(is_admin=is_admin, with_packages=combined).get_fieldset()
    return fieldsets[fs_name]

def get_package_group_fieldset():
    if not 'new_package_group_fs' in fieldsets:
        # new_package_group_fs is the packages for the WUI form
        builder = FormBuilder(model.Member)
        builder.add_field(PackageNameField('package_name'))
        builder.set_field_option('package_name', 'with_renderer', PackagesRenderer)
        builder.set_field_text('package_name', _('Package'))
        builder.set_displayed_fields({_('Add packages'):['package_name']},
                                     focus_field=False)
        fieldsets['new_package_group_fs'] = builder.get_fieldset()
    return fieldsets['new_package_group_fs']
    
def get_group_dict(group=None):
    indict = {}
    if group:
        fs = get_group_fieldset().bind(group)
    else:
        fs = get_group_fieldset()

    exclude = ('-id', '-roles', '-created')

    for field in fs._fields.values():
        if not filter(lambda x: field.renderer.name.endswith(x), exclude):
            if field.renderer.value:
                indict[field.renderer.name] = field.renderer.value
            else:
                indict[field.renderer.name] = u''

            # some fields don't bind in this way, so do it manually
            if field.renderer.name.endswith('-packages'):
                indict[field.renderer.name] = [pkg.name for pkg in group.packages] if group else []

    return indict

def edit_group_dict(_dict, changed_items, id=''):
    prefix = 'Group-%s-' % id
    for key, value in changed_items.items():
        if key:
            if not key.startswith(prefix):
                key = prefix + key
            if _dict.has_key(key):
                _dict[key] = value
    return _dict
