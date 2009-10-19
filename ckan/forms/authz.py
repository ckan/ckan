import formalchemy as fa

import ckan.model as model
import ckan.authz as authz
import ckan.lib.helpers as ckan_h
from formalchemy import helpers as fa_h

import formalchemy.config

from formalchemy import Field
from sqlalchemy import types
def get_package_linker(action):
    return lambda item: '<a href="%s" title="%s"><img src="http://m.okfn.org/kforge/images/icon-delete.png" alt="%s" class="icon" /></a>' % (
                        ckan_h.url_for(controller='package',
                            action='authz',
                            id=item.package.name,
                            role_to_delete=item.id),
                        action,
                        action)

def get_group_linker(action):
    return lambda item: '<a href="%s" title="%s"><img src="http://m.okfn.org/kforge/images/icon-delete.png" alt="%s" class="icon" /></a>' % (
                        ckan_h.url_for(controller='group',
                            action='authz',
                            id=item.group.name,
                            role_to_delete=item.id),
                        action,
                        action)

class RolesRenderer(formalchemy.fields.FieldRenderer):
    def render(self, **kwargs):
        selected = kwargs.get('selected', None) or unicode(self._value)
        options = model.Role.get_all()
        select = fa_h.select(self.name, fa_h.options_for_select(options, selected=selected), **kwargs)
        return select

def get_authz_fieldset(role_class):
    fs = fa.Grid(role_class)
    role_options = model.Role.get_all()

    if role_class == model.PackageRole:
        fs.append(
            Field(u'delete', types.String, get_package_linker(u'delete')).readonly()
            )
    elif role_class == model.GroupRole:
        fs.append(
            Field(u'delete', types.String, get_group_linker(u'delete')).readonly()
            )
    fs.append(
        # use getattr because thought we should always have a user name
        # sometimes (due to error) we don't and want to avoid a 500 ...
        Field(u'username', types.String,
            lambda item: getattr(item.user, 'name', 'No User!')).readonly()
        )

    fs.configure(
        options = [
            fs.role.with_renderer(RolesRenderer),
            ],
        include=[fs.username,
                 fs.role,
                 fs.delete],
        )
    return fs

package_authz_fs = get_authz_fieldset(model.PackageRole)
group_authz_fs = get_authz_fieldset(model.GroupRole)

class UsersRenderer(formalchemy.fields.FieldRenderer):
    def render(self, options, **kwargs):
        options = [('', '__null_value__')] + [(u.name, u.id) for u in model.User.query.all()]
        return fa_h.select(self.name, fa_h.options_for_select(options), **kwargs)

def get_new_role_fieldset(role_class):
    fs = fa.FieldSet(role_class)
    role_options = model.Role.get_all()
    fs.configure(
        include=[
            fs.user,
            fs.role
        ],
        options = [
            fs.user.with_renderer(UsersRenderer),
            fs.role.dropdown(options=role_options)
        ],
        )
    return fs

new_package_roles_fs = get_new_role_fieldset(model.PackageRole)
new_group_roles_fs = get_new_role_fieldset(model.GroupRole)
