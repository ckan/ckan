import formalchemy
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
group_fs.add(Field('New Package 1').dropdown(
    options=[ (p.name, p.name) for p in model.Package.query.all()]
    ))

group_fs.configure(
    options=[
        group_fs.name.label('Name (required)').validate(group_name_validator),
        # group_fs.packages.checkbox(options=_get_packages),
            # GetPackagesHack(group_fs.packages)),
    ],
    exclude=[
        group_fs.id,
        group_fs.packages,
        group_fs.roles,
    ]
)
