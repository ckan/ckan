"""The base Controller API

Provides the BaseController class for subclassing, and other objects
utilized by Controllers.
"""
import logging

from pylons import c, cache, config, g, request, response, session
from pylons.controllers import WSGIController
from pylons.controllers.util import abort, etag_cache, redirect_to
from pylons.decorators import jsonify, validate
from pylons.i18n import _, ungettext, N_
from pylons.templating import render

import ckan
import ckan.lib.helpers as h
import ckan.model as model

PAGINATE_ITEMS_PER_PAGE = 50

class ValidationException(Exception):
    pass

class BaseController(WSGIController):
    repo = model.repo
    log = logging.getLogger(__name__)

    def __before__(self, action, **params):
        # what is different between session['user'] and environ['REMOTE_USER']
        c.__version__ = ckan.__version__
        c.user = request.environ.get('REMOTE_USER', None)
        c.remote_addr = request.environ.get('REMOTE_ADDR', 'Unknown IP Address')
        if c.remote_addr == 'localhost' or c.remote_addr == '127.0.0.1':
            # see if it was proxied
            c.remote_addr = request.environ.get('HTTP_X_FORWARDED_FOR',
                    '127.0.0.1')
        if c.user:
            c.user = c.user.decode('utf8')
            c.author = c.user
        else:
            c.author = c.remote_addr
        c.author = unicode(c.author)
        c.has_paginate = False
        c.has_autocomplete = False

    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        # WSGIController.__call__ dispatches to the Controller method
        # the request is routed to. This routing information is
        # available in environ['pylons.routes_dict']
        try:
            return WSGIController.__call__(self, environ, start_response)
        finally:
            model.Session.remove()

    def _paginate_list(self, register_name, id, template_path, listed_attr_names=['name']):
        c.has_paginate = True
        c.listed_attr_names = listed_attr_names
        c.action = 'list'
        try:
            current_page = int(id)
        except:
            current_page = 1

        register = getattr(model, register_name.capitalize())
        query = register.query
        if hasattr(register.c, 'state_id'):
            active = model.State.query.filter_by(name='active').one()
            query = query.filter_by(state_id=active.id)
        collection = query.all()
        item_count = len(collection)
        if c.format == 'json':
            response.headers['Content-Type'] = 'text/plain'
            list_name = '%s-list' % register_name
            list_value = [{'id': i.name} for i in collection]
            return simplejson.dumps({list_name: list_value})
        else:
            from ckan.lib.helpers import paginate
            c.page = paginate.Page(
                collection=collection,
                page=current_page,
                items_per_page=PAGINATE_ITEMS_PER_PAGE,
                item_count=item_count,
            )
            c.register_name = register_name + 's'
            #if 'paginatedlist' in request.params:
            #    template_path = 'paginated_list_contents'
            return render(template_path)

# Include the '_' function in the public names
__all__ = [__name for __name in locals().keys() if not __name.startswith('_') \
           or __name == '_']
