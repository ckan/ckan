import logging

from ckan.lib.base import request, c, g, render, BaseController
from ckan.lib.jsonp import jsonpify
import ckan.model as model

logger = logging.getLogger('ckan.controllers')


class AuthorizationGroupController(BaseController):
    @jsonpify
    def autocomplete(self):
        q = request.params.get('q', '')
        limit = request.params.get('limit', 20)
        try:
            limit = int(limit)
        except:
            limit = 20
        limit = min(50, limit)
    
        query = model.AuthorizationGroup.search(q)
        def convert_to_dict(user):
            out = {}
            for k in ['id', 'name']:
                out[k] = getattr(user, k)
            return out
        query = query.limit(limit)
        out = map(convert_to_dict, query.all())
        return out

