from ckan.lib.base import BaseController, abort, _
import ckan.model as model

class WebstoreController(BaseController):
    def read(self, id):
        resource = model.Session.query(model.Resource).get(id)
        if not resource:
            abort(404)
        return resource.id

    def write(self, id):
        abort(401, _('Not authorized to see this page'))

