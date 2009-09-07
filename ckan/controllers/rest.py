import datetime

import sqlalchemy.orm
import simplejson

from ckan.controllers.base import *
import ckan.model as model
import ckan.forms
from ckan.lib.search import Search, SearchOptions

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
            obj = model.Package.by_name(id)
            if obj is None:
                response.status_int = 404
                return ''
            _dict = self._convert_object_to_dict(obj)
            _dict['tags'] = [tag.name for tag in obj.tags]
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
        if not self._check_access():
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

            model.repo.commit()        
        except Exception, inst:
            model.Session.rollback()
            raise
        obj = fs.model
        return self._finish_ok(self._convert_object_to_dict(obj))
            
    def update(self, register, id):
        if not self._check_access():
            return simplejson.dumps("Access denied")
        try:
            request_data = self._get_request_data()
        except ValueError, inst:
            response.status_int = 400
            return "JSON Error: %s" % str(inst)

        pkg = model.Package.by_name(id)
        if not pkg:
            response.status_int = 404
            return ''

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
        return self._finish_ok(self._convert_object_to_dict(obj))

    def delete(self, register, id):
        if not self._check_access():
            return simplejson.dumps("Access denied")

        pkg = model.Package.by_name(id)
        if not pkg:
            response.status_int = 404
            return ''
            
        try:
            pkg.delete()
            model.repo.commit()        
        except Exception, inst:
            raise

        return self._finish_ok()

    def search(self):
        if request.params.has_key('q'):
            params = request.params
        elif request.params.has_key('qjson'):
            params = simplejson.loads(request.params['qjson'])
            if not params.has_key('q'):
                response.status_int = 400
                return ''                
        else:
            params = self._get_request_data()
            if not params.has_key('q'):
                response.status_int = 400
                return ''                
        options = SearchOptions(params)
        options.search_tags = False
        options.return_objects = False
        results = Search().run(options)
        return self._finish_ok(results)

    def _check_access(self):
        api_key = None
        isOk = False
        keystr = request.environ.get('HTTP_AUTHORIZATION', None)
        if keystr is None:
            keystr = request.environ.get('Authorization', None)
        self.log.debug("Received API Key: %s" % keystr)
        api_key = model.ApiKey.query.filter_by(key=keystr).first()
        if api_key is not None:
            self.rest_api_user = api_key.name
            self.log.debug("Access OK.")
            response.status_int = 200
            return True
        else:
            self.log.debug("API Key Not Authorized: %s" % keystr)
            response.status_int = 403
            response.headers['Content-Type'] = 'application/json'
            return False

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

    def _convert_object_to_dict(self, obj):
        out = {}
        table = sqlalchemy.orm.class_mapper(obj).mapped_table
        for key in table.c.keys():
            val  = getattr(obj, key)
            if isinstance(val, datetime.date):
                val = str(val)
            out[key] = val
        return out

    def _convert_dict_to_object(self, _dict, _class=model.Package):
        tmp_dict = {}
        for key, value in _dict.items():
            tmp_dict[str(key)] = value

        if 'name' in tmp_dict:
            obj = _class.by_name(tmp_dict['name'])
        else:
            obj = _class()
        for key, value in tmp_dict.items():
            setattr(obj, key, value)

        return obj
        
    def _finish_ok(self, response_data=None):
        response.status_int = 200
        response.headers['Content-Type'] = 'application/json'
        if response_data:
            return simplejson.dumps(response_data)
        else:
            return ''

