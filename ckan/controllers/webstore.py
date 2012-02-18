from ckan.lib.base import BaseController
import ckan.model as model

class WebstoreController(BaseController):
    def data(self, id):
        resource = model.Session.query(model.Resource).get(id)
        if not resource:
            abort(404)
        return resource.id

