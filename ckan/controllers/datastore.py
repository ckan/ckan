from ckan.lib.base import BaseController, abort, _, c, response, request, g
import ckan.model as model
from ckan.lib.jsonp import jsonpify
from ckan.logic import get_action, check_access
from ckan.logic import NotFound, NotAuthorized



class DatastoreController(BaseController):
    def _make_redirect(self, id, url=''):
        index_name = 'ckan-%s' % g.site_id
        query_string = request.environ['QUERY_STRING']
        redirect = "/elastic/%s/%s%s?%s" % (index_name, id, url, query_string)
        # headers must be ascii strings
        response.headers['X-Accel-Redirect'] = str(redirect)

    @jsonpify
    def read(self, id, url=''):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}

        try:
            resource = get_action('resource_show')(context, {'id': id})
            self._make_redirect(id, url)
            return ''
        except NotFound:
            abort(404, _('Resource not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read resource %s') % id)

    @jsonpify
    def write(self, id, url):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}
        try:
            check_access('resource_update', context, {'id': id})
            resource_dict = get_action('resource_show')(context,{'id':id})
            if not resource_dict['webstore_url']:
                resource_dict['webstore_url'] = u'active'
                get_action('resource_update')(context,resource_dict)

            self._make_redirect(id, url)
            return ''
        except NotFound:
            abort(404, _('Resource not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read resource %s') % id)
