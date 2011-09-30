import formalchemy
from formalchemy import helpers as fa_h
import ckan.lib.helpers as h

from builder import FormBuilder
from sqlalchemy.util import OrderedDict
import ckan.model as model
import common
from common import ExtrasField, UserNameField
from ckan.lib.helpers import literal

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

def build_authorization_group_form(is_admin=False, with_users=False):
    builder = FormBuilder(model.AuthorizationGroup)
    builder.set_field_text('name', 'Name', literal("<br/><strong>Unique identifier</strong> for group.<br/>2+ chars, lowercase, using only 'a-z0-9' and '-_'"))
    builder.set_field_option('name', 'validate', common.group_name_validator)
    builder.set_field_option('name', 'required')
    displayed_fields = ['name']
    if with_users:
        builder.add_field(UsersField('users'))
        displayed_fields.append('users')
    builder.set_displayed_fields(OrderedDict([('Details', displayed_fields)]))
    builder.set_label_prettifier(common.prettify)
    return builder  

fieldsets = {}

def get_authorization_group_fieldset(combined=False, is_admin=False):
    if not 'authz_group_fs' in fieldsets:
        # group_fs has no packages - first half of the WUI form
        fieldsets['authz_group_fs'] = build_authorization_group_form(is_admin=is_admin)\
            .get_fieldset()
        
        # group_fs_combined has packages - used for REST interface
        fieldsets['authz_group_fs_combined'] = build_authorization_group_form(
                                                    is_admin=is_admin, 
                                                    with_users=True).get_fieldset()
    if combined:
        return fieldsets['authz_group_fs_combined']
    return fieldsets['authz_group_fs']

def get_authorization_group_user_fieldset():
    if not 'new_user_authz_group_fs' in fieldsets:
        builder = FormBuilder(model.AuthorizationGroupUser)
        builder.add_field(UserNameField('user_name'))
        builder.set_field_option('user_name', 'with_renderer', UsersRenderer)
        builder.set_displayed_fields({'Add users':['user_name']}, focus_field=False)
        fieldsets['new_user_authz_group_fs'] = builder.get_fieldset()
    return fieldsets['new_user_authz_group_fs']
   
