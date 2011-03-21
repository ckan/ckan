from package import *
from group import *
from authorization_group import *
from registry import *
from authz import *
from package_dict import *

from ckan.model.types import JsonType
from formalchemy import forms
import formalchemy
forms.FieldSet.default_renderers[JsonType] = formalchemy.fields.TextFieldRenderer

class GetPackageFieldset(object):

    def __init__(self, **kwds):
        self.kwds = kwds
        if 'user_editable_groups' not in self.kwds:
            self.kwds['user_editable_groups'] = []
        self.fieldset = get_package_fieldset(**kwds)


class GetEditFieldsetPackageData(object):

    def __init__(self, fieldset, package, data):
        self.fieldset = fieldset
        self.package = package
        self.set_data(data)

    def set_data(self, new_data):
        old_data = get_package_dict(pkg=self.package, fs=self.fieldset)
        self.data = edit_package_dict(old_data, new_data, id=self.package.id)


