import formalchemy as fa

import ckan.model as model
import ckan.authz as authz
import ckan.lib.helpers as ckan_h
from formalchemy import helpers as fa_h

import formalchemy.config

from formalchemy import Field
from sqlalchemy import types

__all__ = ['get_authz_fieldset']

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

def get_authorization_group_linker(action):
    return lambda item: '<a href="%s" title="%s"><img src="http://m.okfn.org/kforge/images/icon-delete.png" alt="%s" class="icon" /></a>' % (
                        ckan_h.url_for(controller='authorization_group',
                            action='authz',
                            id=item.authorization_group.name,
                            role_to_delete=item.id),
                        action,
                        action)

class RolesRenderer(formalchemy.fields.FieldRenderer):
    def render(self, **kwargs):
        selected = kwargs.get('selected', None) or unicode(self.value)
        options = [(role, role) for role in model.Role.get_all()]
        select = fa_h.select(self.name, selected, options, **kwargs)
        return select

def authz_fieldset_builder(role_class):
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
    elif role_class == model.AuthorizationGroupRole:
        fs.append(
            Field(u'delete', types.String, get_authorization_group_linker(u'delete')).readonly()
            )
        
    fs.append(
            # use getattr because though we should always have a user name,
            # sometimes (due to error) we don't and want to avoid a 500 ...
            Field(u'username', types.String,
                lambda item: ckan_h.linked_user(getattr(item.user, 'name', ''))).readonly()
            )
            
    fs.append(
            Field(u'authzgroupname', types.String,
                lambda item: getattr(item.authorized_group, 'name', '')).readonly()
            )

    fs.configure(
        options = [
            fs.role.with_renderer(RolesRenderer),
            ],
        include=[fs.username,
                 fs.authzgroupname,
                 fs.role,
                 fs.delete],
        )
    return fs

class UsersRenderer(formalchemy.fields.FieldRenderer):
    def render(self, options, **kwargs):
        options = [('', '__null_value__')] + [(u.display_name, u.id) for u in model.Session.query(model.User).all()]
        selected = None
        return fa_h.select(self.name, selected, options, **kwargs)

class AuthorizationGroupsRenderer(formalchemy.fields.FieldRenderer):
    def render(self, options, **kwargs):
        options = [('', '__null_value__')] + [(u.name, u.id) for u in model.Session.query(model.AuthorizationGroup).all()]
        selected = None
        return fa_h.select(self.name, selected, options, **kwargs)

def get_new_role_fieldset(role_class):
    fs = fa.FieldSet(role_class, session=model.Session)
    role_options = model.Role.get_all()
    fs.configure(
        include=[
            fs.user,
            fs.authorized_group,
            fs.role
        ],
        options = [
            fs.user.with_renderer(UsersRenderer),
            fs.authorized_group.with_renderer(AuthorizationGroupsRenderer),
            fs.role.dropdown(options=role_options)
        ],
        )
    return fs


fieldsets = {}
def get_authz_fieldset(name):
    if not fieldsets: 
        fieldsets['package_authz_fs'] = authz_fieldset_builder(model.PackageRole)
        fieldsets['group_authz_fs'] = authz_fieldset_builder(model.GroupRole)
        fieldsets['authorization_group_authz_fs'] = authz_fieldset_builder(model.AuthorizationGroupRole)
        fieldsets['new_package_roles_fs'] = get_new_role_fieldset(model.PackageRole)
        fieldsets['new_group_roles_fs'] = get_new_role_fieldset(model.GroupRole)
        fieldsets['new_authorization_group_roles_fs'] = \
            get_new_role_fieldset(model.AuthorizationGroupRole)
    return fieldsets[name]
