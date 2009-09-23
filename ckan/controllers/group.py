import genshi

from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController, ValidationException
from simplejson import dumps
import ckan.authz as authz
import ckan.forms

class GroupController(CkanBaseController):
    def __init__(self):
        CkanBaseController.__init__(self)
        self.authorizer = authz.Authorizer()
    
    def index(self):
        return self.list()

    def list(self, id=0):
        return self._paginate_list('group', id, 'group/list', ['name', 'title'])

    def read(self, id):
        c.group = model.Group.by_name(id)
        if c.group is None:
            abort(404)
        c.auth_for_edit = self.authorizer.am_authorized(c, model.Action.EDIT_PERMISSIONS, c.group)
        
        fs = ckan.forms.group_fs.bind(c.group)
        c.content = genshi.HTML(self._render_group(fs))

        return render('group/read')

    def edit(self, id=None): # allow id=None to allow posting
        c.error = ''
        group = model.Group.by_name(id)
        if group is None:
            abort(404, '404 Not Found')
        am_authz = self.authorizer.am_authorized(c, model.Action.EDIT, group)
        if not am_authz:
            abort(401, 'User %r unauthorized to edit %r' % (c.user, id))

        if not 'commit' in request.params:
            c.group = group
            c.groupname = group.name
            
            fs = ckan.forms.group_fs.bind(c.group)
            c.form = self._render_edit_form(fs)
            return render('group/edit')
        else:
            # id is the name (pre-edited state)
            c.groupname = id
            # needed because request is nested
            # multidict which is read only
            params = dict(request.params)
            c.fs = ckan.forms.group_fs.bind(group, data=params or None)
            try:
                self._update(c.fs, id, group.id)
                # do not use groupname from id as may have changed
                c.groupname = c.fs.name.value
                h.redirect_to(action='read', id=c.groupname)
            except ValidationException, error:
                c.error, fs = error.args
                c.form = self._render_edit_form(fs)
                return render('group/edit')

    def _render_edit_form(self, fs):
        # errors arrive in c.error and fs.errors
        c.fieldset = fs
        return render('group/edit_form')

    def _render_group(self, fs):
        # note: doesn't render package list
        c.group_name = fs.name.value
        c.group_title = fs.title.value
        import ckan.misc
        format = ckan.misc.MarkdownFormat()
        desc_formatted = format.to_html(fs.description.value)
        desc_formatted = genshi.HTML(desc_formatted)
        c.group_description_formatted = desc_formatted
        preview = render('group/read_content')
        return preview

    def _update(self, fs, group_name, group_id):
        '''
        Writes the POST data (associated with a group edit) to the database
        @input c.error
        '''
        validation = fs.validate_on_edit(group_name, group_id)
        if not validation:
            errors = []            
            for field, err_list in fs.errors.items():
                errors.append("%s:%s" % (field.name, ";".join(err_list)))
            c.error = ', '.join(errors)
            c.form = self._render_edit_form(fs)
            raise ValidationException(c.error, fs)

        try:
            fs.sync()
        except Exception, inst:
            model.Session.rollback()
            raise
        else:
            model.Session.commit()

