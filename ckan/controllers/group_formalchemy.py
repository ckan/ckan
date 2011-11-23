
import logging

from ckan.lib.base import BaseController, render, c, model, abort, request
from ckan.lib.base import redirect, _, config, h
import ckan.logic.action.create as create
import ckan.logic.action.update as update
import ckan.logic.action.get as get
from ckan.lib.navl.dictization_functions import DataError, unflatten
from ckan.logic import NotFound, NotAuthorized, ValidationError, check_access
from ckan.logic.schema import group_form_schema
from ckan.logic import tuplize_dict, clean_dict
from ckan.authz import Authorizer
import ckan.forms as forms
import ckan.forms
from ckan.lib.base import ValidationException
from ckan.controllers.group import GroupController

from ckan.plugins import PluginImplementations, IGroupController

log = logging.getLogger(__name__)

class GroupFormalchemyController(GroupController):

    def __init__(self):
        self.extensions = PluginImplementations(IGroupController)

    def new(self):
        record = model.Group
        c.error = ''
        
        try:
            context = {'model': model, 'user': c.user or c.author}
            check_access('group_create',context)
        except NotAuthorized:
            abort(401, _('Unauthorized to create a group'))
        
        is_admin = self.authorizer.is_sysadmin(c.user)
        fs = ckan.forms.get_group_fieldset(is_admin=is_admin)

        if request.params.has_key('save'):
            rev = model.repo.new_revision()
            rev.author = c.author
            # needed because request is nested
            # multidict which is read only
            params = dict(request.params)
            c.fs = fs.bind(record, data=params or None, session=model.Session)
            try:
                self._update(c.fs, id, record.id)
            except ValidationException, error:
                fs = error.args[0]
                c.form = self._render_edit_form(fs)
                return render('group/edit.html')
            # do not use groupname from id as may have changed
            c.groupname = c.fs.name.value
            c.grouptitle = c.fs.title.value
            group = model.Group.get(c.groupname)
            assert group
            admins = []
            user = model.User.by_name(c.user)
            admins = [user]
            model.setup_default_user_roles(group, admins)
            group = model.Group.get(c.groupname)
            pkgs = [model.Package.by_name(name) for name in request.params.getall('Group-packages-current')]
            group.packages = pkgs
            pkgnames = request.params.getall('Member--package_name')
            for pkgname in pkgnames:
                if pkgname:
                    package = model.Package.by_name(pkgname)
                    if package and package not in group.packages:
                        group.packages.append(package)
            for extension in self.extensions:
                extension.create(group)
            model.repo.commit_and_remove()
            h.redirect_to(controller='group', action='read', id=c.groupname)

        if request.params:
            data = forms.edit_group_dict(ckan.forms.get_group_dict(), request.params)
            fs = fs.bind(data=data, session=model.Session)
        c.form = self._render_edit_form(fs)
        return render('group/new.html')

    def edit(self, id=None): # allow id=None to allow posting
        c.error = ''
        group = model.Group.get(id)
        if group is None:
            abort(404, '404 Not Found')

        context = {'model': model, 'user': c.user or c.author, 'group':group}
        try:
            check_access('group_update',context)
        except NotAuthorized:
            abort(401, _('User %r not authorized to edit %s') % (c.user, group.id))
        try:
            check_access('group_change_state',context)
            auth_for_change_state = True
        except NotAuthorized:
            auth_for_change_state = False
        
        if not 'save' in request.params:
            c.group = group
            c.groupname = group.name
            c.grouptitle = group.title
            
            fs = forms.get_group_fieldset(is_admin=auth_for_change_state).bind(c.group)
            c.form = self._render_edit_form(fs)
            return render('group/edit.html')
        else:
            rev = model.repo.new_revision()
            rev.author = c.author
            # id is the name (pre-edited state)
            c.groupname = id
            # needed because request is nested
            # multidict which is read only
            params = dict(request.params)
            fs = ckan.forms.get_group_fieldset(is_admin=auth_for_change_state)
            c.fs = fs.bind(group, data=params or None)
            try:
                self._update(c.fs, id, group.id)
                # do not use groupname from id as may have changed
                c.groupname = c.fs.name.value
                c.grouptitle = c.fs.title.value
            except ValidationException, error:
                fs = error.args[0]
                c.form = self._render_edit_form(fs)
                return render('group/edit.html')
            pkgs = [model.Package.by_name(name) for name in request.params.getall('Group-packages-current')]
            group.packages = pkgs
            pkgnames = request.params.getall('Member--package_name')
            for pkgname in pkgnames:
                if pkgname:
                    package = model.Package.by_name(pkgname)
                    if package and package not in group.packages:
                        group.packages.append(package)
            for extension in self.extensions: 
                extension.edit(group)
            model.repo.commit_and_remove()
            h.redirect_to(controller='group', action='read', id=c.groupname)
