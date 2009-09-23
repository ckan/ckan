import formalchemy as fa

import ckan.model as model
import ckan.authz as authz
import ckan.lib.helpers as h
from formalchemy import helpers as fa_h

import formalchemy.config

from formalchemy import Field
from sqlalchemy import types
def get_linker(action):
    return lambda item: '<a href="%s" title="%s"><img src="http://m.okfn.org/kforge/images/icon-delete.png" alt="%s" class="icon" /></a>' % (
                        h.url_for(controller='package',
                            action='authz',
                            id=item.package.name,
                            role_to_delete=item.id),
                        action,
                        action)

authz_fs = fa.Grid(model.PackageRole)
role_options = model.Role.get_all()

authz_fs.add(
    Field(u'delete', types.String, get_linker(u'delete')).readonly()
    )
authz_fs.add(
    Field(u'username', types.String, lambda item: item.user.name).readonly()
    )

authz_fs.configure(
    options = [
        authz_fs.role.dropdown(options=role_options)
        ],
    include=[authz_fs.username,
             authz_fs.role,
             authz_fs.delete],
    )

def get_user_options(fs):
    return [ ('', '__null_value__') ] + [ (u.name, u.id) for u in
            model.User.query.all() ]

class UserOptionsHack(object):
    def __iter__(self):
        opts = get_user_options(None)
        return opts.__iter__()

new_roles_fs = fa.FieldSet(model.PackageRole)
new_roles_fs.configure(
    include=[
        new_roles_fs.user,
        new_roles_fs.role
    ],
    options = [
        # this is supposed to work according to FA docs!
        # new_roles_fs.user.dropdown(options=get_user_options),
        new_roles_fs.user.dropdown(options=UserOptionsHack()),
        new_roles_fs.role.dropdown(options=role_options)
    ],
)

