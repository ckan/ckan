from ckan.lib.base import *
import ckan.forms
from ckan.controllers.base import CkanBaseController
import genshi
from formencode.api import Invalid
from sqlobject.main import SQLObjectNotFound
import simplejson

class PackageController(CkanBaseController):

    repo = model.repo

    def index(self):
        rev = self.repo.youngest_revision()
        c.package_count = len(rev.model.packages)
        return render('package/index')

    def list(self, id, format='html'):
        c.format = format
        return self._paginate_list('packages', id, 'package/list')

    @validate(schema=ckan.forms.PackageNameSchema(), form='new')
    
    def new(self):
        return render('package/new')

    def create(self, format='html'):
        c.error = ''
        c.name = ''
        schema = ckan.forms.PackageNameSchema()
        txn = self.repo.begin_transaction()
        if not request.params.has_key('name'):
            abort(400, '400 Bad Request -- Missing name request parameter.')
        name = request.params['name']
        try:
            pkg = txn.model.packages.get(name)
        except SQLObjectNotFound:
            pass
        else:
            response.status_code = 409  # "409 Conflict"
            c.error = "Package name '%s' is already in use." % name
            # Todo: In-form error indication.
            return render('package/create')
        try:
            c.name = schema.to_python(request.params)['name']
        except Invalid, inst:
            response.status_code = 400
            c.error = "Invalid request: " + str(inst)
            return render('package/create')
        pkg = txn.model.packages.create(name=c.name)
        txn.author = c.author
        txn.log_message = 'Creating package %s' % c.name
        txn.commit()
        if format == 'html':
            return render('package/create')
        elif format == 'json':
            response.status_code = 201
            del(response.headers['Content-Type'])
            return ''
    
    def read(self, id, format='html'):
        rev = self.repo.youngest_revision()
        try:
            pkg = rev.model.packages.get(id)
            if not pkg:
                raise Exception, "Package not found."
        except:
            return self.abort404(format)
        schema = ckan.forms.PackageSchema()
        c.pkg = pkg
        defaults = schema.from_python(pkg)
        if format == 'html':
            c.content = genshi.HTML(self._render_package(defaults))
            return render('package/read')
        elif format == 'json':
            response.status_code = 200
            response.headers['Content-Type'] = 'text/plain'
            data = {
                'name': id,
                #'title': defaults.get('title', ''),
                #'url': self.url,
                #'downloadurl': self.downloadurl,
                #'name': self.name,
                #'license': self.license.name,
                #'notes': self.notes,
            }
            return simplejson.dumps(data)

    def abort404(self, format):
        abort(404, '404 Not Found')

    def _render_package(self, indict):
        # Todo: More specific error handling (don't catch-all and set 500)?
        try:
            c.pkg_name = indict['name']
            c.pkg_title = indict['title']
            c.pkg_url = indict['url']
            c.pkg_download_url = indict['download_url']
            c.pkg_license = indict['licenses']
            c.pkg_tags = indict['tags'].split()
            import ckan.misc
            format = ckan.misc.MarkdownFormat()
            notes_formatted = format.to_html(indict['notes'])
            notes_formatted = genshi.HTML(notes_formatted)
            c.pkg_notes_formatted = notes_formatted
            preview = render('package/read_content')
        except Exception, inst:
            self.status_code = 500
            preview = 'There was an error rendering the package: %s' % inst
        return preview

    # TODO: support validation again ...
    # @validate(schema=ckan.forms.PackageSchema(), form='edit')
    def edit(self, id, format='html'):
        # Todo: Fix up REST format.
        c.has_autocomplete = True
        if request.params.has_key('preview'):
            # Show edit form with inserted package preview.
            indict = dict(request.params)
            c.form = self._render_edit_form(indict)
            c.preview = genshi.HTML(self._render_package(indict))
            return render('package/edit')
        elif request.params.has_key('commit'):
            error = self._update()
            if error:
                c.error = error
                return render('package/update')
            else:
                h.redirect_to(action='read', id=id)
        else:
            # Just show the edit form.
            rev = self.repo.youngest_revision()
            try:
                c.pkg = rev.model.packages.get(id)
            except:
                return self.abort404(format)
            schema = ckan.forms.PackageSchema()
            defaults = schema.from_python(c.pkg)
            c.form = self._render_edit_form(defaults)
            return render('package/edit')
    
    def _render_edit_form(self, value_dict):
        from formencode import htmlfill
        rev = self.repo.youngest_revision()
        all_licenses = list(model.License.select()) 
        if value_dict.has_key('licenses'):
            selected = value_dict['licenses']
        else:
            selected = []
        c.license_options = h.options_for_select_from_objects(
                all_licenses,
                selected=selected,
                name_attr='name')
        content = render('package/edit_form')
        form = htmlfill.render(content, value_dict)
        return form

    def update(self):
        c.error = self._update()
        return render('package/update')

    def _is_locked(self):
        # allow non-existent name -- never happens but allows test of 'bad'
        # update (test_update in test_package.py) to work normally :)
        c.pkg_name = request.params.get('name', '')
        if c.pkg_name == 'mis-uiowa':
            msg = 'This package is temporarily locked and cannot be edited'
            raise msg
        return ''

    def _is_spam(self, log_message):
        if 'http:' in log_message:
            return True
        return False

    def _update(self):
        error_msg = self._is_locked()
        if error_msg:
            return locked
        schema = ckan.forms.PackageSchema()
        indict = dict(request.params)
        # currently only returns one value because of problems with
        # genshi and multiple on select so need to wrap in an array
        if request.params.has_key('licenses'):
            indict['licenses'] = [request.params['licenses']]
        else:
            indict['licenses'] = []
        txn = self.repo.begin_transaction()
        txn.author = c.author
        log_message = indict.get('log_message', '')
        if self._is_spam(log_message):
            error_msg = 'This commit looks like spam'
            return error_msg
        txn.log_message = log_message
        try:
            pkg = schema.to_python(indict, state=txn)
        except Invalid, inst:
            response.status_code = 400
            error_msg = "Invalid request: " + str(inst)
        else:
            c.pkg_name = pkg.name
            txn.commit()
        return error_msg

