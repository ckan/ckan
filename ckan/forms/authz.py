import formalchemy as fa

import ckan.model as model
import ckan.authz as authz
import ckan.lib.helpers as h
from formalchemy import helpers as fa_h

import formalchemy.config

from formalchemy import Field
from sqlalchemy import types
def get_package_linker(action):
    return lambda item: '<a href="%s" title="%s"><img src="http://m.okfn.org/kforge/images/icon-delete.png" alt="%s" class="icon" /></a>' % (
                        h.url_for(controller='package',
                            action='authz',
                            id=item.package.name,
                            role_to_delete=item.id),
                        action,
                        action)

def get_group_linker(action):
    return lambda item: '<a href="%s" title="%s"><img src="http://m.okfn.org/kforge/images/icon-delete.png" alt="%s" class="icon" /></a>' % (
                        h.url_for(controller='group',
                            action='authz',
                            id=item.group.name,
                            role_to_delete=item.id),
                        action,
                        action)

def get_authz_fieldset(role_class):
    fs = fa.Grid(role_class)
    role_options = model.Role.get_all()

    if role_class == model.PackageRole:
        fs.add(
            Field(u'delete', types.String, get_package_linker(u'delete')).readonly()
            )
    elif role_class == model.GroupRole:
        fs.add(
            Field(u'delete', types.String, get_group_linker(u'delete')).readonly()
            )
    fs.add(
        Field(u'username', types.String, lambda item: item.user.name).readonly()
        )

    fs.configure(
        options = [
            fs.role.dropdown(options=role_options)
            ],
        include=[fs.username,
                 fs.role,
                 fs.delete],
        )
    return fs

package_authz_fs = get_authz_fieldset(model.PackageRole)
group_authz_fs = get_authz_fieldset(model.GroupRole)

def get_user_options(fs):
    return [ ('', '__null_value__') ] + [ (u.name, u.id) for u in
            model.User.query.all() ]

class UserOptionsHack(object):
    def __iter__(self):
        opts = get_user_options(None)
        print "USERS", opts
        return opts.__iter__()

def get_new_role_fieldset(role_class):
    fs = fa.FieldSet(role_class)
    role_options = model.Role.get_all()
    fs.configure(
        include=[
            fs.user,
            fs.role
        ],
        options = [
            # this is supposed to work according to FA docs!
            # fs.user.dropdown(options=get_user_options),
            fs.user.dropdown(options=UserOptionsHack()),
            fs.role.dropdown(options=role_options)
        ],
        )
    return fs

new_package_roles_fs = get_new_role_fieldset(model.PackageRole)
new_group_roles_fs = get_new_role_fieldset(model.GroupRole)
