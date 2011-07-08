import logging

import urlparse
from ckan.lib.base import BaseController, render, c, model, abort, request
from ckan.lib.base import  config, h, ValidationException
from ckan.lib.package_saver import PackageSaver
from ckan.controllers.package import PackageController
import ckan.forms
from pylons.i18n import get_lang, _

log = logging.getLogger(__name__)

class PackageFormalchemyController(PackageController):

    def new(self):
        c.error = ''
        api_url = config.get('ckan.api_url', '/').rstrip('/')
        c.package_create_slug_api_url = api_url+h.url_for(controller='api', action='create_slug')
        is_admin = self.authorizer.is_sysadmin(c.user)
        # Check access control for user to create a package.
        auth_for_create = self.authorizer.am_authorized(c, model.Action.PACKAGE_CREATE, model.System())
        if not auth_for_create:
            abort(401, _('Unauthorized to create a package'))
        # Get the name of the package form.
        try:
            fs = self._get_package_fieldset(is_admin=is_admin)
        except ValueError, e:
            abort(400, e)
        if 'save' in request.params or 'preview' in request.params:
            if not request.params.has_key('log_message'):
                abort(400, ('Missing parameter: log_message'))
            log_message = request.params['log_message']
        record = model.Package
        if request.params.has_key('save'):
            fs = fs.bind(record, data=dict(request.params) or None, session=model.Session)
            try:
                PackageSaver().commit_pkg(fs, log_message, c.author, client=c)
                pkgname = fs.name.value

                pkg = model.Package.by_name(pkgname)
                admins = []
                if c.user:
                    user = model.User.by_name(c.user)
                    if user:
                        admins = [user]
                model.setup_default_user_roles(pkg, admins)
                for item in self.extensions:
                    item.create(pkg)
                model.repo.commit_and_remove()

                self._form_save_redirect(pkgname, 'new')
            except ValidationException, error:
                fs = error.args[0]
                c.form = self._render_edit_form(fs, request.params,
                        clear_session=True)
                return render('package/new.html')
            except KeyError, error:
                abort(400, ('Missing parameter: %s' % error.args).encode('utf8'))

        # use request params even when starting to allow posting from "outside"
        # (e.g. bookmarklet)
        if 'preview' in request.params or 'name' in request.params or 'url' in request.params:
            if 'name' not in request.params and 'url' in request.params:
                url = request.params.get('url')
                domain = urlparse.urlparse(url)[1]
                if domain.startswith('www.'):
                    domain = domain[4:]
            # ensure all fields specified in params (formalchemy needs this on bind)
            from ckan.forms import add_to_package_dict,get_package_dict

            data = add_to_package_dict(get_package_dict(fs=fs), request.params)
            fs = fs.bind(model.Package, data=data, session=model.Session)

        else:
            fs = fs.bind(session=model.Session)
        #if 'preview' in request.params:
        #    c.preview = ' '
        c.form = self._render_edit_form(fs, request.params, clear_session=True)
        if 'preview' in request.params:
            c.is_preview = True
            try:
                PackageSaver().render_preview(fs,
                                              log_message=log_message,
                                              author=c.author, client=c)
                c.preview = h.literal(render('package/read_core.html'))
            except ValidationException, error:
                fs = error.args[0]
                c.form = self._render_edit_form(fs, request.params,
                        clear_session=True)
                return render('package/new.html')
        return render('package/new.html')

    def edit(self, id=None): # allow id=None to allow posting
        # TODO: refactor to avoid duplication between here and new
        c.error = ''
        c.pkg = pkg = model.Package.get(id)
        if pkg is None:
            abort(404, '404 Not Found')
        model.Session().autoflush = False
        am_authz = self.authorizer.am_authorized(c, model.Action.EDIT, pkg)
        if not am_authz:
            abort(401, _('User %r not authorized to edit %s') % (c.user, id))

        auth_for_change_state = self.authorizer.am_authorized(c, model.Action.CHANGE_STATE, pkg)
        try:
            fs = self._get_package_fieldset(is_admin=auth_for_change_state)
        except ValueError, e:
            abort(400, e)
        if 'save' in request.params or 'preview' in request.params:
            if not request.params.has_key('log_message'):
                abort(400, ('Missing parameter: log_message'))
            log_message = request.params['log_message']

        if not 'save' in request.params and not 'preview' in request.params:
            # edit
            c.pkgname = pkg.name
            c.pkgtitle = pkg.title
            if pkg.license_id:
                self._adjust_license_id_options(pkg, fs)
            fs = fs.bind(pkg)
            c.form = self._render_edit_form(fs, request.params)
            return render('package/edit.html')
        elif request.params.has_key('save'):
            # id is the name (pre-edited state)
            pkgname = id
            params = dict(request.params) # needed because request is nested
                                          # multidict which is read only
            fs = fs.bind(pkg, data=params or None)
            try:
                for item in self.extensions:
                    item.edit(fs.model)
                PackageSaver().commit_pkg(fs, log_message, c.author, client=c)
                # do not use package name from id, as it may have been edited
                pkgname = fs.name.value
                self._form_save_redirect(pkgname, 'edit')
            except ValidationException, error:
                fs = error.args[0]
                c.form = self._render_edit_form(fs, request.params,
                                                clear_session=True)
                return render('package/edit.html')
            except KeyError, error:
                abort(400, 'Missing parameter: %s' % error.args)
        else: # Must be preview
            c.is_preview = True
            c.pkgname = pkg.name
            c.pkgtitle = pkg.title
            if pkg.license_id:
                self._adjust_license_id_options(pkg, fs)
            fs = fs.bind(pkg, data=dict(request.params))
            try:
                PackageSaver().render_preview(fs,
                                              log_message=log_message,
                                              author=c.author, client=c)
                c.pkgname = fs.name.value
                c.pkgtitle = fs.title.value
                read_core_html = render('package/read_core.html') #utf8 format
                c.preview = h.literal(read_core_html)
                c.form = self._render_edit_form(fs, request.params)
            except ValidationException, error:
                fs = error.args[0]
                c.form = self._render_edit_form(fs, request.params,
                        clear_session=True)
                return render('package/edit.html')
            return render('package/edit.html') # uses c.form and c.preview
