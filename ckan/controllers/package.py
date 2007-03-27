from ckan.lib.base import *
import ckan.forms

class PackageController(BaseController):
    repo = model.repo

    def __before__(self, action, **params):
        # what is different between session['user'] and environ['REMOTE_USER']
        c.user = session.get('user', None)
        c.remote_addr = request.environ.get('REMOTE_ADDR', 'Unknown IP Address')
        if c.user:
            c.author = self.c.user
        else:
            c.author = c.remote_addr

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
        return render_response('package/read')

    def list(self):
        rev = self.repo.youngest_revision()
        packages = rev.model.packages.list()
        c.package_count = len(packages)
        c.packages = packages
        return render_response('package/list')

    def update(self):
        c.error = ''
        if not request.params.has_key('name'):
            c.error = 'No package name was specified'
        else:
            c.pkg_name = request.params['name']
            try:
                schema = ckan.forms.PackageSchema()
                # currently only returns one value because of problems with
                # genshi and multiple on select so need to wrap in an array
                indict = dict(request.params)
                indict['licenses'] = [request.params['licenses']]
                txn = self.repo.begin_transaction()
                txn.author = c.author
                txn.log_message = indict.get('log_message', '')
                pkg = schema.to_python(indict, state=txn)
                txn.commit()
            except Exception, inst:
                c.error = '%s' % inst
        return render_response('package/update')

    @validate(schema=ckan.forms.PackageSchema(), form='edit')
    def edit(self, id):
        # TODO insert the existing object content or raise and error if there
        # is no package with than id
        from formencode import htmlfill
        rev = self.repo.youngest_revision()
        c.pkg = rev.model.packages.get(id)
        all_licenses = list(model.License.select()) 
        if c.pkg.license is not None:
            selected = [ c.pkg.license.id ]
        else:
            selected = []
        c.license_options = h.options_for_select_from_objects(
                all_licenses,
                selected=selected,
                name_attr='name')
        content = render('package/edit_form')
        schema = ckan.forms.PackageSchema()
        defaults = schema.from_python(c.pkg)
        c.form = htmlfill.render(content, defaults)
        return render_response('package/edit')

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
