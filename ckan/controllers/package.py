from ckan.lib.base import *
import ckan.forms

class PackageController(BaseController):

    def index(self):
        c.package_count = model.Package.select().count()
        return render_response('package/index')

    def read(self, id):
        try:
            c.pkg = model.Package.byName(id)
        except:
            abort(404)
        return render_response('package/read')

    def list(self):
        packages = list(model.Package.select())
        c.package_count = len(packages)
        c.packages = packages
        return render_response('package/list')

    def update(self):
        c.error = ''
        if not request.params.has_key('name'):
            c.error = 'No package name was specified'
        else:
            try:
                name = request.params['name']
                rev = model.dm.begin_revision()
                pkg = model.dm.packages.get(name, revision=rev)
                pkg.url = request.params['url']
                rev.commit()
            except Exception, inst:
                c.error = '%s' % inst
        return render_response('package/update')

    @validate(schema=ckan.forms.PackageSchema(), form='edit')
    def edit(self, id):
        # TODO insert the existing object content or raise and error if there
        # is no package with than id
        from formencode import htmlfill
        c.pkg = model.dm.packages.get(id)
        content = render('package/edit_form')
        schema = ckan.forms.PackageSchema()
        defaults = schema.from_python(c.pkg)
        c.form = htmlfill.render(content, defaults)
        # htmlfill.render uses HTMLParser which returns broken xhtml
        # also strips of ending </form>
        return render_response('package/edit')

    def create(self):
        c.error = ''
        # should validate I suppose
        try:
            rev = model.dm.begin_revision()
            newdict = dict(request.params)
            pkg = model.dm.packages.create(
                    revision=rev,
                    name=request.params['name'],
                    url=request.params.get('url', ''),
                    notes=request.params.get('notes', '')
                    )
            rev.commit()
        except Exception, inst:
            c.error = '%s' % inst
        return render_response('package/create')
    
    @validate(schema=ckan.forms.PackageSchema(), form='new')
    def new(self):
        return render_response('package/new')
