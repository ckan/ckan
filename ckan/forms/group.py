import formalchemy
from formalchemy import helpers as h

import ckan.model as model
import common

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

def _get_packages(fs):
    out = [ (p.name, p.id) for p in fs.model.packages ]
    print '********', out
    print fs.parent.model.packages
    print fs.model.packages
    return out

class GetPackagesHack(object):
    def __init__(self, fs):
        self.fs = fs

    def __iter__(self):
        out = _get_packages(self.fs)
        return out.__iter__()


group_fs = GroupFieldSet()
from formalchemy import Field

group_fs.configure(
    options=[
        group_fs.name.label('Name (required)').with_renderer(common.CustomTextFieldRenderer).validate(group_name_validator),
        group_fs.title.with_renderer(common.CustomTextFieldRenderer),
        group_fs.description.with_renderer(common.TextAreaRenderer),
        # group_fs.packages.checkbox(options=_get_packages),
            # GetPackagesHack(group_fs.packages)),
    ],
    exclude=[
        group_fs.id,
        group_fs.packages,
        group_fs.roles,
    ]
)

class PackagesRenderer(formalchemy.fields.FieldRenderer):
    def render(self, **kwargs):
        selected = unicode(kwargs.get('selected', None) or self._value)
        options = [('', '__null_value__')] + [(p.name, p.id) for p in model.Package.query.all()]
        return h.select(self.name, h.options_for_select(options, selected=selected), **kwargs)

##group_fs.add(Field('New Package 1').dropdown(
##    options=[ (p.name, p.name) for p in model.Package.query.all()]
##    ))
package_list = [('', '__null_value__')] + [(p.name, p.id) for p in model.Package.query.all()]
new_package_group_fs = formalchemy.FieldSet(model.PackageGroup)
new_package_group_fs.configure(
    options=[new_package_group_fs.package_id.with_renderer(PackagesRenderer)],
    include=[new_package_group_fs.package_id]
    )
