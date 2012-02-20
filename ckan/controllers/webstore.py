from ckan.lib.base import BaseController, abort, _, c
import ckan.model as model
from ckan.logic import get_action, check_access
from ckan.logic import NotFound, NotAuthorized, ValidationError

class WebstoreController(BaseController):
    def read(self, id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}

        try:
            resource = get_action('resource_show')(context, {'id': id})
            return resource['id']
        except NotFound:
            abort(404, _('Resource not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read resource %s') % id)

    def write(self, id):
        abort(401, _('Not authorized to see this page'))

