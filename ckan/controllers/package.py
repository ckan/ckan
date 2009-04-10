import logging
import genshi
import simplejson
import formencode

from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController
from ckan.searchquerybuilder import SearchQueryBuilder
import ckan.forms

logger = logging.getLogger('ckan.controllers')

class PackageController(CkanBaseController):

    def index(self):
        c.package_count = model.Package.query.count()
        return render('package/index')

    def list(self, id, format='html'):
        c.format = format
        return self._paginate_list('package', id, 'package/list',
            ['name', 'title'])

    def search(self):
        request_params = dict(request.params)
        c.show_results = False
        if request_params.has_key('q'):
            c.show_results = True
            c.q = request_params['q']
            mode = MockMode('package', model.Package, request_params)
            builder = SearchQueryBuilder(mode)
            query = builder.execute()
            if query is None:
                c.packages = []
            else:
                c.packages = query.all()
            c.package_count = len(c.packages)
        return render('package/search')

    def read(self, id):
        pkg = model.Package.by_name(id)
        if pkg is None:
            abort(404, '404 Not Found')

        schema = ckan.forms.PackageSchema()
        c.pkg = pkg
        defaults = schema.from_python(pkg)
        c.content = genshi.HTML(self._render_package(defaults))
        return render('package/read')

    def history(self, id):
        c.pkg = model.Package.by_name(id)
        if not c.pkg:
            abort(404, '404 Not Found')
        c.revisions = c.pkg.all_revisions
        return render('package/history')

    # Try to use this again ...
    # @validate(schema=ckan.forms.PackageNameSchema(), form='new')
    def new(self):
        c.has_autocomplete = True
        c.error = ''
        if not 'commit' in request.params and not 'preview' in request.params:
            defaults = {}
            c.form = self._render_edit_form(defaults)
            return render('package/new')
        elif request.params.has_key('commit'):
            c.pkgname = request.params['name']
            try:
                self._update()
            except formencode.Invalid, error:
                c.error = error
                indict = dict(request.params)
                c.form = self._render_edit_form(indict, c.error)
                return render('package/new')
            # TODO: ?
            # except Exception, error:
            #   raise if in debug mode?
            h.redirect_to(action='read', id=c.pkgname)
        else: # Must be preview
            indict = dict(request.params)
            c.form = self._render_edit_form(indict)
            c.preview = genshi.HTML(self._render_package(indict))
            return render('package/new')

    # TODO: use this decorator again
    # @validate(schema=ckan.forms.PackageSchema(), form='edit')
    def edit(self, id=None): # allow id=None to allow posting
        # TODO: refactor to avoid duplication between here and new
        c.has_autocomplete = True
        c.error = ''
        if not 'commit' in request.params and not 'preview' in request.params:
            c.pkg = model.Package.by_name(id)
            if c.pkg is None:
                abort(404, '404 Not Found')
            c.pkgname = id
            schema = ckan.forms.PackageSchema()
            defaults = schema.from_python(c.pkg)
            c.form = self._render_edit_form(defaults)
            return render('package/edit')
        elif request.params.has_key('commit'):
            # do not use pkgname from id as may have changed
            c.pkgname = request.params['name']
            try:
                self._update()
                h.redirect_to(action='read', id=c.pkgname)
            except formencode.Invalid, error:
                c.error = error
                indict = dict(request.params)
                c.form = self._render_edit_form(indict, c.error)
                return render('package/edit')
            # TODO: ?
            # except Exception, error:
            #   raise if in debug mode?
        else: # Must be preview
            c.pkgname = request.params['name']
            indict = dict(request.params)
            c.form = self._render_edit_form(indict)
            c.preview = genshi.HTML(self._render_package(indict))
            return render('package/edit')

        c.has_autocomplete = True
        if request.params.has_key('preview'):
            indict = dict(request.params)
            c.form = self._render_edit_form(indict)
            c.preview = genshi.HTML(self._render_package(indict))
            return render('package/edit')
        elif request.params.has_key('commit'):
            error = self._update()
            if error:
                c.error = error
                return render('package/edit')
            else:
                h.redirect_to(action='read', id=id)
        else:
            c.pkg = model.Package.by_name(id)
            if c.pkg is None:
                abort(404, '404 Not Found')
            schema = ckan.forms.PackageSchema()
            defaults = schema.from_python(c.pkg)
            c.form = self._render_edit_form(defaults)
            return render('package/edit')
    
    def _render_edit_form(self, value_dict, errors=None):
        from formencode import htmlfill
        all_licenses = model.LicenseList.all_formatted
        if value_dict.has_key('licenses'):
            selected = value_dict['licenses'] # already names not objects
        else:
            selected = []
        c.license_options = h.options_for_select(
                # insert empty option
                [''] + all_licenses,
                selected=selected
                )
        content = render('package/edit_form')
        errs = errors.unpack_errors() if errors else {}
        form = htmlfill.render(content, value_dict, errs)
        return form

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
            raise Exception(error_msg)
        indict = dict(request.params)
        log_message = indict.get('log_message', '')
        if self._is_spam(log_message):
            error_msg = 'This commit looks like spam'
            # TODO: make this into a UserErrorMessage or the like
            raise Exception(error_msg)

        # currently only returns one value because of problems with
        # genshi and multiple on select so need to wrap in an array
        if request.params.has_key('licenses'):
            indict['licenses'] = [request.params['licenses']]
        else:
            indict['licenses'] = []
        schema = ckan.forms.PackageSchema()
        try:
            rev = model.repo.new_revision()
            rev.author = c.author
            rev.message = log_message
            pkg = schema.to_python(indict)
        except Exception, inst:
            model.Session.rollback()
            raise
        else:
            model.Session.commit()

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

class MockMode(object):

    def __init__(self, register_name, register, request_data={'q': ''}):
        self.register_name = register_name
        self.register = register
        self.request_data = request_data

    def get_register_name(self):
        return self.register_name

    def get_register(self):
        return self.register



