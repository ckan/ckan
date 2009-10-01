import formalchemy
from formalchemy import helpers as h

import ckan.model as model
import common

__all__ = ['group_fs', 'group_fs_combined', 'new_package_group_fs', 'get_group_dict', 'edit_group_dict']

def group_name_validator(val):
    common.name_validator(val)
    if model.Group.by_name(val):
        raise formalchemy.ValidationError('Group name already exists in database')

class GroupFieldSet(formalchemy.FieldSet):
    def __init__(self):
        formalchemy.FieldSet.__init__(self, model.Group)

    def validate_on_edit(self, orig_group_name, record_id):
        # If not changing name, don't validate this field (it will think it
        # is not unique because name already exists in db). So change it
        # temporarily to something that will always validate ok.
        temp_name = None
        if self.name.value == orig_group_name:
            temp_name = orig_group_name
            self.data['Group-%s-name' % record_id] = u'something_unique'
        validation = self.validate()
        if temp_name:
            # restore it
            self.data['Group-%s-name' % record_id] = temp_name
        return validation

class PackageEditRenderer(formalchemy.fields.FieldRenderer):
    def deserialize(self):
        packages_as_string = unicode(self._serialized_value())
        group = self.field.parent.model

        packages_as_string = packages_as_string.replace(',', ' ')
        pkg_list = packages_as_string.split()
        packages = [model.Package.by_name(pkg_name) for pkg_name in pkg_list]
        return packages        

class PackagesField(formalchemy.Field):
    def sync(self):
        if not self.is_readonly():
            self._update_packages()

    def _update_packages(self):
        group = self.model
        packages = self._deserialize()
        group.packages = packages

group_fs = GroupFieldSet() # has no packages
group_fs_combined = GroupFieldSet() # has packages

group_fs_combined.add(PackagesField('packages').with_renderer(PackageEditRenderer)) #.validate(common.package_names_validator))

group_fs.configure(
    options=[
        group_fs.name.label('Name (required)').with_renderer(common.CustomTextFieldRenderer).validate(group_name_validator),
        group_fs.title.with_renderer(common.CustomTextFieldRenderer),
        group_fs.description.with_renderer(common.TextAreaRenderer),
    ],
    exclude=[
        group_fs.id,
        group_fs.packages,
        group_fs.roles,
    ]
)

group_fs_combined.configure(
    options=[
        group_fs.name.label('Name (required)').validate(group_name_validator),
        ],
    exclude=[
        group_fs.id,
        group_fs.roles,
        ]
)

class PackagesRenderer(formalchemy.fields.FieldRenderer):
    def render(self, **kwargs):
        selected = unicode(kwargs.get('selected', None) or self._value)
        options = [('', '__null_value__')] + [(p.name, p.id) for p in model.Package.query.all()]
        return h.select(self.name, h.options_for_select(options, selected=selected), **kwargs)

new_package_group_fs = formalchemy.FieldSet(model.PackageGroup)
new_package_group_fs.configure(
    options=[new_package_group_fs.package_id.with_renderer(PackagesRenderer)],
    include=[new_package_group_fs.package_id]
    )

def get_group_dict(group=None):
    indict = {}
    if group:
        fs = group_fs.bind(group)
    else:
        fs = group_fs

    exclude = ('-id', '-roles')

    for field in fs._fields.values():
        if not filter(lambda x: field.renderer.name.endswith(x), exclude):
             if field.renderer._value:
                 indict[field.renderer.name] = field.renderer._value
             else:
                 indict[field.renderer.name] = u''
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

def validate_group_on_edit(fs, id):
    # If not changing name, don't validate this field (it will think it
    # is not unique because name already exists in db). So change it
    # temporarily to something that will always validate ok.
    temp_name = None
    if fs.name.value == id:
        temp_name = id
        fs.data['Group-%s-name' % record_id] = u'something_unique'
    validation = fs.validate()
    if temp_name:
        # restore it
        fs.data['Group-%s-name' % record_id] = temp_name
