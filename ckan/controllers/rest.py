import sqlalchemy.orm
import simplejson

from ckan.controllers.base import *
import ckan.model as model
import ckan.forms
from ckan.lib.search import Search, SearchOptions
import ckan.authz

class RestController(CkanBaseController):

    def index(self):
        return render('rest/index')

    def list(self, register):
        if register == u'package':
            packages = model.Package.query.all() 
            results = [package.name for package in packages]
            return self._finish_ok(results)
        elif register == u'tag':
            tags = model.Tag.query.all() #TODO
            results = [tag.name for tag in tags]
            return self._finish_ok(results)
        else:
            response.status_int = 400
            return ''

    def show(self, register, id):
        if register == u'package':
            pkg = model.Package.by_name(id)
            if pkg is None:
                response.status_int = 404
                return ''

            if not self._check_access(pkg, model.Action.READ):
                return ''

            _dict = pkg.as_dict()
            #TODO check it's not none
            return self._finish_ok(_dict)
        elif register == u'tag':
            obj = model.Tag.by_name(id) #TODO tags
            if obj is None:
                response.status_int = 404
                return ''            
            _dict = [pkgtag.package.name for pkgtag in obj.package_tags]
            return self._finish_ok(_dict)
        else:
            response.status_int = 400
            return ''

    def create(self, register):
        if not self._check_access(None, None):
            return simplejson.dumps("Access denied")
        try:
            request_data = self._get_request_data()
        except ValueError, inst:
            response.status_int = 400
            return "JSON Error: %s" % str(inst)
        try:
            request_fa_dict = ckan.forms.edit_package_dict(ckan.forms.get_package_dict(), request_data)
            fs = ckan.forms.package_fs.bind(model.Package, data=request_fa_dict)
            validation = fs.validate()
            if not validation:
                response.status_int = 409
                return simplejson.dumps(repr(fs.errors))
            rev = model.repo.new_revision()
            rev.author = self.rest_api_user
            rev.message = u'REST API: Create object %s' % str(fs.name.value)
            fs.sync()

            # set default permissions
            if self.rest_api_user:
                admins = [model.User.by_name(self.rest_api_user)]
            else:
                admins = []
            model.setup_default_user_roles(fs.model, admins)

            model.repo.commit()        
        except Exception, inst:
            model.Session.rollback()
            raise
        obj = fs.model
        return self._finish_ok(obj.as_dict())
            
    def update(self, register, id):
        pkg = model.Package.by_name(id)
        if not pkg:
            response.status_int = 404
            return ''

        if not self._check_access(pkg, model.Action.EDIT):
            return simplejson.dumps("Access denied")

        try:
            request_data = self._get_request_data()
        except ValueError, inst:
            response.status_int = 400
            return "JSON Error: %s" % str(inst)


        try:
            orig_pkg_dict = ckan.forms.get_package_dict(pkg)
            request_fa_dict = ckan.forms.edit_package_dict(orig_pkg_dict, request_data, id=pkg.id)
            fs = ckan.forms.package_fs.bind(pkg, data=request_fa_dict)
            validation = fs.validate_on_edit(pkg.name, pkg.id)
            if not validation:
                response.status_int = 409
                return simplejson.dumps(repr(fs.errors))
            rev = model.repo.new_revision()
            rev.author = self.rest_api_user
            rev.message = u'REST API: Update object %s' % str(fs.name.value)
            fs.sync()

            model.repo.commit()        
        except Exception, inst:
            model.Session.rollback()
            if inst.__class__.__name__ == 'IntegrityError':
                response.status_int = 409
                return ''
            else:
                raise
        obj = fs.model
        return self._finish_ok(obj.as_dict())

    def delete(self, register, id):
        pkg = model.Package.by_name(id)
        if not pkg:
            response.status_int = 404
            return ''

        if not self._check_access(pkg, model.Action.PURGE):
            return simplejson.dumps("Access denied")
            
        try:
            pkg.delete()
            model.repo.commit()        
        except Exception, inst:
            raise

        return self._finish_ok()

    def search(self):
        if request.params.has_key('qjson'):
            params = simplejson.loads(request.params['qjson'])
        elif request.params.values() and request.params.values() != [u'']:
            params = request.params
        else:
            params = self._get_request_data()
        options = SearchOptions(params)
        options.search_tags = False
        options.return_objects = False
        results = Search().run(options)
        return self._finish_ok(results)

    def _check_access(self, pkg, action):
        # Checks apikey is okay and user is authorized to do the specified
        # action on the specified package. If both args are None then just
        # the apikey is checked.
        api_key = None
        isOk = False
        keystr = request.environ.get('HTTP_AUTHORIZATION', None)
        if keystr is None:
            keystr = request.environ.get('Authorization', None)
        self.log.debug("Received API Key: %s" % keystr)
        api_key = model.User.query.filter_by(apikey=keystr).first()
        if api_key is not None:
            self.rest_api_user = api_key.name
        else:
            self.rest_api_user = ''

        if action and pkg:
            am_authz = ckan.authz.Authorizer().is_authorized(self.rest_api_user, action, pkg)
            if not am_authz:
                self.log.debug("User is not authorized to %s %s" % (action, pkg))
                response.status_int = 403
                response.headers['Content-Type'] = 'application/json'
                return False
        elif not self.rest_api_user:
            self.log.debug("API key not authorized: %s" % keystr)
            response.status_int = 403
            response.headers['Content-Type'] = 'application/json'
            return False
        self.log.debug("Access OK.")
        response.status_int = 200
        return True                

    def _get_request_data(self):
        try:
            request_data = request.params.keys()[0]
        except Exception, inst:
            msg = "Can't find entity data in request params %s: %s" % (
                request.params.items(), str(inst)
            )
            raise Exception, msg
        request_data = simplejson.loads(request_data)
        return request_data
        
    def _finish_ok(self, response_data=None):
        response.status_int = 200
        response.headers['Content-Type'] = 'application/json'
        if response_data:
            return simplejson.dumps(response_data)
        else:
            return ''

