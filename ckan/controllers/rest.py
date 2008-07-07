from ckan.controllers.base import *
import simplejson
from ckan.modes import RegisterGet, RegisterPost, RegisterSearch
from ckan.modes import EntityGet, EntityPut, EntityDelete
import ckan.model as model

class RestController(CkanBaseController):

    def index(self):
        return render('rest/index')

    def list(self, register):
        registry_path = '/%s' % register
        self.log.debug("Listing: %s" % registry_path)
        self.mode = RegisterGet(registry_path).execute()
        return self.finish()

    def create(self, register):
        if not self.check_access():
            return simplejson.dumps("Access denied")
        registry_path = '/%s' % register
        try:
            request_data = self._get_request_data()
        except ValueError, inst:
            response.status_code = 400
            return "JSON Error: %s" % str(inst)
        self.log.debug("Creating: %s with %s" % (registry_path, request_data))
        self.mode = RegisterPost(registry_path, request_data).execute()
        return self.finish()

    def show(self, register, id):
        id = self.fix_id(id)
        registry_path = '/%s/%s' % (register, id)
        self.log.debug("Reading: %s" % registry_path)
        self.mode = EntityGet(registry_path).execute()
        return self.finish()

    def update(self, register, id):
        if not self.check_access():
            return simplejson.dumps("Access denied")
        id = self.fix_id(id)
        registry_path = '/%s/%s' % (register, id)
        try:
            request_data = self._get_request_data()
        except ValueError, inst:
            response.status_code = 400
            return "JSON Error: %s" % str(inst)
        if 'id' in request_data:
            request_data.pop('id')
        self.log.debug("Updating: %s with %s" % (registry_path, request_data))
        self.mode = EntityPut(registry_path, request_data).execute()
        return self.finish()

    def delete(self, register, id):
        if not self.check_access():
            return simplejson.dumps("Access denied")
        id = self.fix_id(id)
        registry_path = '/%s/%s' % (register, id)
        self.log.debug("Deleting: %s" % registry_path)
        self.mode = EntityDelete(registry_path).execute()
        return self.finish()

    def search(self, register):
        registry_path = '/%s' % register
        request_data = self._get_request_data()
        self.log.debug("Searching: %s" % registry_path)
        self.mode = RegisterSearch(registry_path, request_data).execute()
        return self.finish()

    def finish(self):
        response.status_code = self.mode.response_code
        return simplejson.dumps(self.mode.response_data)

    def fix_id(self, id):
        return id

    def check_access(self):
        api_key = None
        isOk = False
        keystr = request.environ.get('HTTP_AUTHORIZATION', None)
        if keystr is None:
            keystr = request.environ.get('Authorization', None)
        if keystr is None:
            keystr = request.params.get('api-key', None)
        api_key_selection = model.ApiKey.select(model.ApiKey.q.key==keystr)
        if api_key_selection.count() > 0:
            api_key = api_key_selection[0]
            c.rest_api_user = api_key.name
            isOk = True
        self.log.debug("Received API Key: %s" % keystr)
        # Follow this way for API authentication, reuses existing passwords?
        # http://developer.yahoo.com/python/python-rest.html#auth
        if isOk:
            self.log.debug("Access OK.")
            response.status_code = 200
            return True
        else:
            self.log.debug("API Key Not Authorized.")
            response.status_code = 403
            return False

    def _get_request_data(self):
        try:
            request_data = request.params.keys()[0]
        except Exception, inst:
            msg = "Can't find entity data in request params %s: %s" % (
                request.params.items(), str(inst)
            )
            raise Exception, msg
        self.log.debug("Loading JSON string: %s" % (request_data))
        request_data = simplejson.loads(request_data)
        self.log.debug("Loaded JSON data: %s" % (request_data))
        return request_data
