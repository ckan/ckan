import formalchemy
from formalchemy import helpers as fa_h
import ckan.lib.helpers as h

from builder import FormBuilder
import ckan.model as model
import common
from ckan.lib.helpers import literal

__all__ = ['get_group_fieldset', 'get_group_dict', 'edit_group_dict']

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
            packages = [model.Package.by_name(pkg_name) for pkg_name in pkg_list]
            return packages        

# For new_package_group_fs
class PackagesRenderer(formalchemy.fields.FieldRenderer):
    def render(self, **kwargs):
        kwargs['class'] = 'autocomplete'
        kwargs['data-autocomplete-url'] = h.url_for(controller='package', action='autocomplete', id=None)
        html = fa_h.text_field(self.name, **kwargs)
        return html

def build_group_form(with_packages=False):
    builder = FormBuilder(model.Group)
    builder.set_field_text('name', 'Unique Name (required)', literal("<br/><strong>Unique identifier</strong> for group.<br/>2+ chars, lowercase, using only 'a-z0-9' and '-_'"))
    builder.set_field_option('name', 'validate', common.group_name_validator)
    builder.set_field_option('description', 'textarea', {'size':'60x15'})
    displayed_fields = ['name', 'title', 'description']
    if with_packages:
        builder.add_field(PackagesField('packages'))
        displayed_fields.append('packages')
    builder.set_displayed_fields({'Details':displayed_fields})
    builder.set_label_prettifier(common.prettify)
    return builder

fieldsets = {}
def get_group_fieldset(name):
    if not fieldsets:
        # group_fs has no packages - first half of the WUI form
        fieldsets['group_fs'] = build_group_form().get_fieldset()
        
        # group_fs_combined has packages - used for REST interface
        fieldsets['group_fs_combined'] = build_group_form(with_packages=True).get_fieldset()

        # new_package_group_fs is the packages for the WUI form
        builder = FormBuilder(model.PackageGroup)
        builder.set_field_option('package_id', 'with_renderer', PackagesRenderer)
        builder.set_displayed_fields({'Add packages':['package_id']},
                                     focus_field=False)
        fieldsets['new_package_group_fs'] = builder.get_fieldset()
    return fieldsets[name]

    
def get_group_dict(group=None):
    indict = {}
    if group:
        fs = get_group_fieldset('group_fs').bind(group)
    else:
        fs = get_group_fieldset('group_fs')

    exclude = ('-id', '-roles', '-created')

    for field in fs._fields.values():
        if not filter(lambda x: field.renderer.name.endswith(x), exclude):
            if field.renderer._value:
                indict[field.renderer.name] = field.renderer._value
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
