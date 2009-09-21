import formalchemy as fa

import ckan.model as model
import ckan.authz as authz
import ckan.lib.helpers as h
from formalchemy import helpers as fa_h

import formalchemy.config

class AuthzFieldSet(fa.Grid):    
##    def __init__(self, c, package=None, data=None):
##        # Same as bind in formalchemy
##        assert package or data, 'Must supply at least one input'
##        assert package, 'Authz field set not designed to create new package'
        
##        self._c = c
##        self.package = None
##        self.data = None
##        self.errors = {}
##        self._authorizer = authz.Authorizer()
        
##        if package:
##            assert isinstance(package, model.Package)        
##            self.package = package

##        if data:
##            assert isinstance(data, dict)
##            self._deserialize(data)
##        else:
##            self._get_data_fromdb()

##        self._visitor = model.User.by_name(model.PSEUDO_USER__VISITOR)
##        self._logged_in = model.User.by_name(model.PSEUDO_USER__LOGGED_IN)

    def __render(self):
        all_roles = model.Role.get_all()
        user_roles = self.data
#        prs = self._authorizer.get_package_roles(self.package)
#        editable = self._authorizer.am_authorized(self._c, model.Action.EDIT_PERMISSIONS, self.package)
        editable = bool(self.data)

        rows = []
        current_user_has_role = False
        first_users = [model.PSEUDO_USER__VISITOR, model.PSEUDO_USER__LOGGED_IN]
        for first_user in first_users:
            if user_roles.has_key(first_user):
                roles = user_roles[first_user]
            else:
                roles = ['']
            for role in roles:
                rows.append((first_user, role))
        for username, roles in user_roles.items():
            if username not in first_users:
                for role in roles:
                    rows.append((username, role))
            if username == self._c.user:
                current_user_has_role = True
        if editable:
            if not current_user_has_role:
                rows.append((self._c.user, ''))
            rows.extend([('', '')]*3)
        
        html = '<span id="authz">'
        html += '<table>\n'
        def make_html_row(items, heading=False):
            item_tag = 'th' if heading else 'td'
            _item = '<%s>%%s</%s>' % (item_tag, item_tag)
            return '<tr> %s </tr>\n' % ' '.join([_item % item for item in items])
        html += make_html_row(['User', 'Role'], heading=True)

        for index, row in enumerate(rows):
            username, role = row
            row_name = '%i' % index
            if username == model.PSEUDO_USER__VISITOR:
                row_title = 'Anyone'
            elif username == model.PSEUDO_USER__LOGGED_IN:
                row_title = 'Anyone logged in'
            else:
                if editable:
                    row_title = h.text('%s-%s' % (row_name, 'username'), value=username)
                else:
                    row_title = username
            if editable:
                options = [(None, '')] + [(_role, _role.capitalize()) for _role in all_roles]
                select = h.select(name='%s-%s' % (row_name, 'role'),
                                  selected_values=role,
                                  options=options)
            else:
                select = role.capitalize()
            row = [row_title, select]
            if self.errors.has_key(index):
                err_str = '&nbsp;<span class="error">Error: %s</span>' % self.errors[index]
                row.append(err_str)
            html += make_html_row(row)
        html += '</table></span>'
        return html

    def __validate(self):
        self.errors = {}
        user_names = self.data_user_names
        for index, username in user_names.items():
            count = model.User.query.filter_by(name=username).count()
            if count == 0:
                self.errors[index] = u'Username \'%s\' is not found' % username
        return not self.errors

    def _get_data_fromdb(self):
        prs = self._authorizer.get_package_roles(self.package)
        user_roles = {}
        for user, role in prs:
            if not user_roles.has_key(user):
                user_roles[user.name] = []
            user_roles[user.name].append(role)
        self.data = user_roles

    def _deserialize(self, data):
        assert isinstance(data, dict)
        
        # sort out table data items into usernames and roles
        usernames = {0:model.PSEUDO_USER__VISITOR,
                     1:model.PSEUDO_USER__LOGGED_IN} # row_index:username
        roles = {} # row_index:role
        for key, value in data.items():
            if key == 'commit':
                continue
            if '-' in key:
                row_index, column = key.split('-')
                row_index = int(row_index)
                if column == 'role':
                    role = value
                    roles[row_index] = role
                elif column == 'username':
                    username = value
                    if value:
                        usernames[row_index] = value

        # combine into table
        user_roles = {} # user:[roles]
        for row_index, username in usernames.items():
            if not user_roles.has_key(username):
                user_roles[username] = []
            role = roles.get(row_index)
            if role:
                user_roles[username].append(role)
        self.data, self.data_user_names = user_roles, usernames

    def _sync(self):
        user_roles = self.data
        # For users given, ensure roles in db match form
        for user_name, roles in user_roles.items():
            user = model.User.by_name(user_name)
            for role in model.Role.get_all():
                value = role in roles
                existing_value = model.user_has_role(user, role, self.package)
                if existing_value == True and value == False:
                    model.remove_user_from_role(user, role, self.package)
                elif existing_value == False and value == True:
                    model.add_user_to_role(user, role, self.package)
        # Any users not on the form are deleted from the roles in db
        for user, role in self._authorizer.get_package_roles(self.package):
            if not user_roles.has_key(user.name):
                model.remove_user_from_role(user, role, self.package)
                

class UserRenderer(fa.FieldRenderer):
    def render(self, options, **kwargs):
        new_options = [('', '__null_value__')] + [(u.name, u.id) for u in model.User.query.all()]
        
        selected_user_id = kwargs.get('selected', None) or self._value
        selected_user = model.User.query.filter_by(id=selected_user_id).first()
        if selected_user:
            selected = selected_user.id
        else:
            selected = '__null_value__'

        return fa_h.select(self.name, fa_h.options_for_select(new_options, selected=selected), **kwargs)

    def validate(self, val):
        return val is not None

authz_fs = fa.Grid(model.PackageRole)
role_options = model.Role.get_all()
authz_fs.configure(
    options = [authz_fs.user.with_renderer(UserRenderer),
               authz_fs.role.dropdown(options=role_options),
               ],
    include=[authz_fs.user,
             authz_fs.role],
    )

    
