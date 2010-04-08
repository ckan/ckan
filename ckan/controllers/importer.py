import logging
import os
import uuid

from pylons import request, response, session, config, tmpl_context as c
from pylons.controllers.util import abort, redirect_to
from ckan.lib.package_saver import PackageSaver, ValidationException
import genshi

from ckan.lib.base import *
import ckan.forms
from licenses import LicenseList

log = logging.getLogger(__name__)

importer_dir = os.path.join(config['pylons.cache_dir'], 'importer')
if not os.path.exists(importer_dir):
    os.makedirs(importer_dir) 

def importer_to_fs_dict(pkg_dict):
    fs_dict = {}
    prefix = 'Package--'
    for key, value in pkg_dict.items():
        fs_key = prefix + key
        fs_dict[fs_key] = value
    return fs_dict

class ImporterController(BaseController):
    authorizer = ckan.authz.Authorizer()

    def index(self):
        return render('importer/importer')

    def preview(self):
        if not c.user:
            abort(401, gettext('Need to login before importing.'))
        c.import_previews = []
        import ckan.lib.importer as importer
        params = dict(request.params)
        if not params.has_key('file'):
            c.error = _('Need to specify a filename.')
            return render('importer/importer')                
        if not hasattr(params['file'], 'value'):
            c.error = _('Did not receive file successfully.')
            return render('importer/importer')
        file_buf = params['file'].value
        # save as temp file for when you do import
        self._save_tempfile(file_buf)
        if not file_buf:
            c.error = _('File \'%s\' not found.') % params['file'].filename
            return render('importer/importer')
        try:
            importer = importer.PackageImporter(buf=file_buf)
        except importer.ImportException, e:
            c.error = _('Error importing file \'%s\' as Excel or CSV format: %s') % (params['file'].filename, e)
            return render('importer/importer')
        c.import_filename = params['file'].filename.lstrip(os.sep)
        if params.has_key('log_message'):
            c.log_message = params['log_message']
        c.fs_list = []
        c.import_previews = []
        count = 0
        all_errors = []
        for fs in self._get_fs(importer):
            count += 1
            errors, warnings, existing_pkg = self._validate(fs)
            if errors:
                all_errors.append(errors)
            if count < 5 or errors or warnings:
                c.import_previews.append(self.package_render(fs, errors, warnings))
            else:
                c.pkgs_suppressed
            c.fs_list.append(fs)
        c.errors = len(all_errors)
        c.num_pkgs = len(c.fs_list)
        return render('importer/preview')

    def do_import(self):
        import ckan.lib.importer as importer
        file_buf = self._load_tempfile()
        try:
            importer = importer.PackageImporter(buf=file_buf)
        except importer.ImportException, e:
            c.error = _('Error importing file \'%s\' as Excel or CSV format: %s') % (params['file'].filename, e)
            return render('importer/importer')
        if 'log_message' in request.params:
            log_message = request.params.getone('log_message')
        else:
            log_message = ''
        count = 0
        for fs in self._get_fs(importer):
            errors, warnings, existing_pkg = self._validate(fs)
            if errors:
                print "Errors: ", errors
                abort(400, gettext('Errors remain - see preview.'))
            try:
                rev = model.repo.new_revision()
                rev.author = c.user
                rev.message = log_message
                fs.sync()
            except Exception, inst:
                model.Session.rollback()
                raise
            
            if not existing_pkg:
                new_pkg = fs.model
                user = model.User.by_name(c.user)
                if not user:
                    abort(401, gettext('Problem with user account.'))
                admins = [user]
                model.setup_default_user_roles(new_pkg, admins)

            count += 1

        model.Session.commit()
        c.message = ungettext('Imported %i package.', 'Imported %i packages.', count) % count
        return render('importer/result')

    def _get_fs(self, importer):
        for index, pkg_dict in enumerate(importer.pkg_dict()):
            pkg = model.Package.by_name(pkg_dict['name'])
            if pkg:
                existing_dict = ckan.forms.get_package_dict(pkg)
                pkg_id = pkg.id
            else:
                existing_dict = ckan.forms.get_package_dict()
                pkg_id = ''
                pkg = model.Package
            fa_dict = ckan.forms.edit_package_dict(existing_dict, pkg_dict, id=pkg_id)
            fs = ckan.forms.get_standard_fieldset()
            fs = fs.bind(pkg, data=fa_dict)
            yield fs
        

    def _save_tempfile(self, buf):
        tmp_filename = str(uuid.uuid4())
        tmp_dir = importer_dir
        tmp_filepath = os.path.join(tmp_dir, tmp_filename)
        f_obj = open(tmp_filepath, 'wb')
        f_obj.write(buf)
        f_obj.close()
        session['import_filename'] = tmp_filename
        session.save()

    def _load_tempfile(self):
        tmp_filename = session['import_filename']
        if not tmp_filename:
            raise ImportException(_('Could not access import file any more.'))
        tmp_dir = importer_dir
        tmp_filepath = os.path.join(tmp_dir, tmp_filename)
        f_obj = open(tmp_filepath, 'rb')
        buf = f_obj.read()
        f_obj.close() 
        return buf

    def _validate(self, fs):
        errors = []
        warnings = []
        if not c.user:
            abort(302, gettext('User is not logged in'))
        else:
            user = model.User.by_name(c.user)
            if not user:
                abort(302, gettext('Error with user account. Log out and log in again.'))
        pkg = model.Package.by_name(fs.name.value)
        if pkg:
            warnings.append(_('Package %s already exists in database. Import will edit the fields.') % fs.name.value)
            am_authz = self.authorizer.am_authorized(c, model.Action.EDIT, pkg)
            if not am_authz:
                 errors.append(_('User %r unauthorized to edit existing package %s') % (c.user, fs.name.value))
        validation = fs.validate()
        if not validation:
            for field, err_list in fs.errors.items():
                errors.append("%s:%s" % (field.name, ";".join(err_list)))
        errors = ', '.join(errors)
        warnings = ', '.join(errors)
        return errors, warnings, pkg

    def package_render(self, fs, errors, warnings):
        try:
            PackageSaver().render_preview(fs, None, None) # create a new package for now
            preview = h.literal(render('package/read_core'))
        except ValidationException, error:
            c.error, fs = error.args
            preview = h.literal('<li>Errors: %s</li>\n') % c.error
        return preview

