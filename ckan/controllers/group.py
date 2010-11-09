import genshi

from sqlalchemy.orm import eagerload_all
from ckan.lib.base import *
from pylons.i18n import get_lang, _
import ckan.authz as authz
import ckan.forms
from ckan.lib.helpers import Page
from ckan.plugins import ExtensionPoint, IGroupController

class GroupController(BaseController):
    
    def __init__(self):
        BaseController.__init__(self)
        self.authorizer = authz.Authorizer()
        self.extensions = ExtensionPoint(IGroupController)
    
    def index(self):
        from ckan.lib.helpers import Page

        query = ckan.authz.Authorizer().authorized_query(c.user, model.Group)
        query = query.options(eagerload_all('packages'))
        c.page = Page(
            collection=query,
            page=request.params.get('page', 1),
            items_per_page=20
        )
        return render('group/index.html')

    def read(self, id):
        c.group = model.Group.by_name(id)
        if c.group is None:
            abort(404)
        auth_for_read = self.authorizer.am_authorized(c, model.Action.READ, c.group)
        if not auth_for_read:
            abort(401, gettext('Not authorized to read %s') % id.encode('utf8'))
        
        import ckan.misc
        format = ckan.misc.MarkdownFormat()
        desc_formatted = format.to_html(c.group.description)
        desc_formatted = genshi.HTML(desc_formatted)
        c.group_description_formatted = desc_formatted
        c.group_admins = self.authorizer.get_admins(c.group)

        c.page = Page(
            collection=c.group.active_packages(),
            page=request.params.get('page', 1),
            items_per_page=50
        )
        for extension in self.extensions:
            extension.read(c.group)
        return render('group/read.html')

    def new(self):
        record = model.Group
        c.error = ''
        
        auth_for_create = self.authorizer.am_authorized(c, model.Action.GROUP_CREATE, model.System())
        if not auth_for_create:
            abort(401, str(gettext('Unauthorized to create a group')))
        
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
            group = model.Group.by_name(c.groupname)
            assert group
            admins = []
            user = model.User.by_name(c.user)
            admins = [user]
            model.setup_default_user_roles(group, admins)
            group = model.Group.by_name(c.groupname)
            pkgs = [model.Package.by_name(name) for name in request.params.getall('Group-packages-current')]
            group.packages = pkgs
            pkgnames = request.params.getall('PackageGroup--package_name')
            for pkgname in pkgnames:
                if pkgname:
                    package = model.Package.by_name(pkgname)
                    if package and package not in group.packages:
                        group.packages.append(package)
            for extension in self.extensions:
                extension.create(group)
            model.repo.commit_and_remove()
            h.redirect_to(action='read', id=c.groupname)

        if request.params:
            data = ckan.forms.edit_group_dict(ckan.forms.get_group_dict(), request.params)
            fs = fs.bind(data=data, session=model.Session)
        c.form = self._render_edit_form(fs)
        return render('group/new.html')

    def edit(self, id=None): # allow id=None to allow posting
        c.error = ''
        group = model.Group.by_name(id)
        if group is None:
            abort(404, '404 Not Found')
        am_authz = self.authorizer.am_authorized(c, model.Action.EDIT, group)
        if not am_authz:
            abort(401, gettext('User %r not authorized to edit %r') % (c.user, id))
            
        auth_for_change_state = self.authorizer.am_authorized(c, model.Action.CHANGE_STATE, group)
        
        if not 'save' in request.params:
            c.group = group
            c.groupname = group.name
            c.grouptitle = group.title
            
            fs = ckan.forms.get_group_fieldset(is_admin=auth_for_change_state).bind(c.group)
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
            pkgnames = request.params.getall('PackageGroup--package_name')
            for pkgname in pkgnames:
                if pkgname:
                    package = model.Package.by_name(pkgname)
                    if package and package not in group.packages:
                        group.packages.append(package)
            for extension in self.extensions: 
                extension.edit(group)
            model.repo.commit_and_remove()
            h.redirect_to(action='read', id=c.groupname)

    def authz(self, id):
        c.group = model.Group.by_name(id)
        if c.group is None:
            abort(404, gettext('Group not found'))
        c.groupname = c.group.name
        c.grouptitle = c.group.title

        c.authz_editable = self.authorizer.am_authorized(c, model.Action.EDIT_PERMISSIONS, c.group)
        if not c.authz_editable:
            abort(401, gettext('Not authorized to edit authorization for group'))

        if 'save' in request.params: # form posted
            # needed because request is nested
            # multidict which is read only
            params = dict(request.params)
            c.fs = ckan.forms.get_authz_fieldset('group_authz_fs').bind(c.group.roles, data=params or None)
            try:
                self._update_authz(c.fs)
            except ValidationException, error:
                # TODO: sort this out 
                # fs = error.args[0]
                # return render('group/authz.html')
                raise
            # now do new roles
            newrole_user_id = request.params.get('GroupRole--user_id')
            newrole_authzgroup_id = request.params.get('GroupRole--authorized_group_id')
            if newrole_user_id != '__null_value__' and newrole_authzgroup_id != '__null_value__':
                c.message = _(u'Please select either a user or an authorization group, not both.')
            elif newrole_user_id != '__null_value__':
                user = model.Session.query(model.User).get(newrole_user_id)
                # TODO: chech user is not None (should go in validation ...)
                role = request.params.get('GroupRole--role')
                newgrouprole = model.GroupRole(user=user, group=c.group,
                        role=role)
                # With FA no way to get new GroupRole back to set group attribute
                # new_roles = ckan.forms.new_roles_fs.bind(model.GroupRole, data=params or None)
                # new_roles.sync()
                for extension in self.extensions:
                    extension.authz_add_role(newgrouprole)
                model.Session.commit()
                model.Session.remove()
                c.message = _(u'Added role \'%s\' for user \'%s\'') % (
                    newgrouprole.role,
                    newgrouprole.user.display_name)
            elif newrole_authzgroup_id != '__null_value__':
                authzgroup = model.Session.query(model.AuthorizationGroup).get(newrole_authzgroup_id)
                # TODO: chech user is not None (should go in validation ...)
                role = request.params.get('GroupRole--role')
                newgrouprole = model.GroupRole(authorized_group=authzgroup, 
                        group=c.group, role=role)
                # With FA no way to get new GroupRole back to set group attribute
                # new_roles = ckan.forms.new_roles_fs.bind(model.GroupRole, data=params or None)
                # new_roles.sync()
                for extension in self.extensions:
                    extensions.authz_add_role(newgrouprole)
                model.Session.commit()
                model.Session.remove()
                c.message = _(u'Added role \'%s\' for authorization group \'%s\'') % (
                    newgrouprole.role,
                    newgrouprole.authorized_group.name)
        elif 'role_to_delete' in request.params:
            grouprole_id = request.params['role_to_delete']
            grouprole = model.Session.query(model.GroupRole).get(grouprole_id)
            if grouprole is None:
                c.error = _(u'Error: No role found with that id')
            else:
                for extension in self.extensions:
                    extension.authz_remove_role(grouprole)
                grouprole.purge()
                if grouprole.user:
                    c.message = _(u'Deleted role \'%s\' for user \'%s\'') % \
                                (grouprole.role, grouprole.user.display_name)
                elif grouprole.authorized_group:
                    c.message = _(u'Deleted role \'%s\' for authorization group \'%s\'') % \
                                (grouprole.role, grouprole.authorized_group.name)
                model.Session.commit()

        # retrieve group again ...
        c.group = model.Group.by_name(id)
        fs = ckan.forms.get_authz_fieldset('group_authz_fs').bind(c.group.roles)
        c.form = fs.render()
        c.new_roles_form = \
            ckan.forms.get_authz_fieldset('new_group_roles_fs').render()
        return render('group/authz.html')
        
    def history(self, id):
        if 'diff' in request.params or 'selected1' in request.params:
            try:
                params = {'id':request.params.getone('group_name'),
                          'diff':request.params.getone('selected1'),
                          'oldid':request.params.getone('selected2'),
                          }
            except KeyError, e:
                if dict(request.params).has_key('group_name'):
                    id = request.params.getone('group_name')
                c.error = _('Select two revisions before doing the comparison.')
            else:
                params['diff_entity'] = 'group'
                h.redirect_to(controller='revision', action='diff', **params)

        c.group = model.Group.by_name(id)
        if not c.group:
            abort(404, gettext('Group not found'))
        format = request.params.get('format', '')
        if format == 'atom':
            # Generate and return Atom 1.0 document.
            from webhelpers.feedgenerator import Atom1Feed
            feed = Atom1Feed(
                title=_(u'CKAN Group Revision History'),
                link=h.url_for(controller='group', action='read', id=c.group.name),
                description=_(u'Recent changes to CKAN Package: ') + (c.group.title or ''),
                language=unicode(get_lang()),
            )
            for revision, obj_rev in c.group.all_related_revisions:
                try:
                    dayHorizon = int(request.params.get('days'))
                except:
                    dayHorizon = 30
                try:
                    dayAge = (datetime.now() - revision.timestamp).days
                except:
                    dayAge = 0
                if dayAge >= dayHorizon:
                    break
                if revision.message:
                    item_title = u'%s' % revision.message.split('\n')[0]
                else:
                    item_title = u'%s' % revision.id
                item_link = h.url_for(controller='revision', action='read', id=revision.id)
                item_description = _('Log message: ')
                item_description += '%s' % (revision.message or '')
                item_author_name = revision.author
                item_pubdate = revision.timestamp
                feed.add_item(
                    title=item_title,
                    link=item_link,
                    description=item_description,
                    author_name=item_author_name,
                    pubdate=item_pubdate,
                )
            feed.content_type = 'application/atom+xml'
            return feed.writeString('utf-8')
        c.group_revisions = c.group.all_related_revisions
        return render('group/history.html')

    def _render_edit_form(self, fs):
        # errors arrive in c.error and fs.errors
        c.fieldset = fs
        c.fieldset2 = ckan.forms.get_package_group_fieldset()
        return render('group/edit_form.html')

    def _update(self, fs, group_name, group_id):
        '''
        Writes the POST data (associated with a group edit) to the database
        @input c.error
        '''
        validation = fs.validate()
        if not validation:
            c.form = self._render_edit_form(fs)
            raise ValidationException(fs)

        try:
            fs.sync()
        except Exception, inst:
            model.Session.rollback()
            raise
        else:
            model.Session.commit()

    def _update_authz(self, fs):
        validation = fs.validate()
        if not validation:
            c.form = self._render_edit_form(fs)
            raise ValidationException(fs)
        try:
            fs.sync()
        except Exception, inst:
            model.Session.rollback()
            raise
        else:
            model.Session.commit()
