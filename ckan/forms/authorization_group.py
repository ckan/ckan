import formalchemy
from formalchemy import helpers as fa_h
import ckan.lib.helpers as h

from builder import FormBuilder
from sqlalchemy.util import OrderedDict
import ckan.model as model
import common
from common import ExtrasField, UserNameField
from ckan.lib.helpers import literal
from pylons.i18n import _

# for group_fs_combined (REST)
class UsersField(common.ConfiguredField):
    def get_configured(self):
        return self.UsersField(self.name).with_renderer(self.UserEditRenderer)

    class UsersField(formalchemy.Field):
        def sync(self):
            if not self.is_readonly():
                self._update_users()

        def _update_packages(self):
            self.model.users = self._deserialize()

    class UserEditRenderer(formalchemy.fields.FieldRenderer):
        def deserialize(self):
            value = self.params[self.name]
            if isinstance(value, list): # from rest i/f
                usrs_list = value
            elif isinstance(value, (unicode, str)): # from form
                users_as_string = unicode(value).replace(',', ' ')
                usrs_list = packages_as_string.split()
            return [model.User.by_name(usr_name) for usr_name in usrs_list]

# For new_package_group_fs
class UsersRenderer(formalchemy.fields.FieldRenderer):
    def render(self, **kwargs):
        kwargs['class'] = 'autocomplete-user'
        html = fa_h.text_field(self.name, **kwargs)
        return html

fieldsets = {}
