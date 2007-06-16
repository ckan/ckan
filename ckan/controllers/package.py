from ckan.lib.base import *
import ckan.forms
from ckan.controllers.base import CkanBaseController
import genshi

class PackageController(CkanBaseController):
    repo = model.repo

    def index(self):
        rev = self.repo.youngest_revision()
        c.package_count = len(rev.model.packages)
        return render_response('package/index')

    def read(self, id):
        try:
            rev = self.repo.youngest_revision()
            c.pkg = rev.model.packages.get(id)
        except:
            abort(404)
        import ckan.misc
        format = ckan.misc.MarkdownFormat()
        notes_formatted = format.to_html(c.pkg.notes)
        notes_formatted = genshi.HTML(notes_formatted)
        c.pkg_notes_formatted = notes_formatted
        return render_response('package/read')

    def list(self):
        rev = self.repo.youngest_revision()
        packages = rev.model.packages.list()
        c.package_count = len(packages)
        c.packages = packages
        return render_response('package/list')

    def _update(self):
        error_msg = ''
        try:
            c.pkg_name = request.params['name']
            schema = ckan.forms.PackageSchema()
            indict = dict(request.params)
            # currently only returns one value because of problems with
            # genshi and multiple on select so need to wrap in an array
            indict['licenses'] = [request.params['licenses']]
            txn = self.repo.begin_transaction()
            txn.author = c.author
            txn.log_message = indict.get('log_message', '')
            pkg = schema.to_python(indict, state=txn)
            txn.commit()
        except Exception, inst:
            error_msg = '%s' % inst
        return error_msg

    def update(self):
        c.error = self._update()
        return render_response('package/update')

    # TODO: support validation again ...
    # @validate(schema=ckan.forms.PackageSchema(), form='edit')
    def edit(self, id):
        # if preview use the dictionary and render the two forms
        if request.params.has_key('preview'):
            indict = dict(request.params)
            c.form = self._render_edit_form(indict)
            c.preview = genshi.HTML(self._render_preview(indict))
            return render_response('package/edit')
        elif request.params.has_key('commit'):
            self._update()
            h.redirect_to(action='read', id=id)
        else: # if neither preview nor save do normal render
            # TODO: check we have a package with this id
            try:
                rev = self.repo.youngest_revision()
                c.pkg = rev.model.packages.get(id)
                schema = ckan.forms.PackageSchema()
                defaults = schema.from_python(c.pkg)
                c.form = self._render_edit_form(defaults)
            except Exception, inst:
                c.form = 'There was an error rendering the preview: %s' % inst
            return render_response('package/edit')
    
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


    def _render_preview(self, indict):
        try:
            c.pkg_url = indict['url']
            c.pkg_license = indict['licenses']
            c.pkg_tags = indict['tags'].split()
            import ckan.misc
            format = ckan.misc.MarkdownFormat()
            notes_formatted = format.to_html(indict['notes'])
            notes_formatted = genshi.HTML(notes_formatted)
            c.pkg_notes_formatted = notes_formatted
            preview = render('package/read_content')
        except Exception, inst:
            preview = 'There was an error rendering the preview: %s' % inst
        return preview

    def create(self):
        c.error = ''
        c.name = ''
        schema = ckan.forms.PackageNameSchema()
        try:
            txn = self.repo.begin_transaction()
            c.name = schema.to_python(request.params)['name']
            pkg = txn.model.packages.create(name=c.name)
            txn.author = c.author
            txn.log_message = 'Creating package %s' % c.name
            txn.commit()
        except Exception, inst:
            c.error = '%s' % inst
        return render_response('package/create')
    
    @validate(schema=ckan.forms.PackageNameSchema(), form='new')
    def new(self):
        return render_response('package/new')
