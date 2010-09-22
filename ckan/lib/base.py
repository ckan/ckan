"""The base Controller API

Provides the BaseController class for subclassing.
"""
import logging

from pylons import c, cache, config, g, request, response, session
from pylons.controllers import WSGIController
from pylons.controllers.util import abort, etag_cache, redirect_to, redirect
from pylons.decorators import jsonify, validate
from pylons.i18n import _, ungettext, N_, gettext
from pylons.templating import cached_template, pylons_globals
from webhelpers.html import literal

import ckan
import ckan.lib.helpers as h
from ckan.config import plugins
from ckan.lib.helpers import json
import ckan.model as model
import os

# nuke cache
#from pylons import cache
#cache.clear()

PAGINATE_ITEMS_PER_PAGE = 50

APIKEY_HEADER_NAME_KEY = 'apikey_header_name'
APIKEY_HEADER_NAME_DEFAULT = 'X-CKAN-API-Key'

def render(template_name, extra_vars=None, cache_key=None, cache_type=None, 
           cache_expire=None, method='xhtml'):
    
    def render_template():
        globs = extra_vars or {}
        globs.update(pylons_globals())
        template = globs['app_globals'].genshi_loader.load(template_name)
        stream = template.generate(**globs)
        
        # extension point for all plugins implementing 'render(self, stream)'.
        for _filter in plugins.find_methods('render'):
            stream = _filter(stream)
        
        return literal(stream.render(method=method, encoding=None))
    
    if 'Pragma' in response.headers:
        del response.headers["Pragma"]
    if cache_key is not None or cache_type is not None:
        response.headers["Cache-Control"] = "public"  
    
    if cache_expire is not None:
        response.headers["Cache-Control"] = "max-age=%s, must-revalidate" % cache_expire
    
    return cached_template(template_name, render_template, cache_key=cache_key, 
                           cache_type=cache_type, cache_expire=cache_expire)
                           #, ns_options=('method'), method=method)


class ValidationException(Exception):
    pass

class BaseController(WSGIController):
    repo = model.repo
    log = logging.getLogger(__name__)

    def __before__(self, action, **params):
        self._start_call_timing()
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

    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        # WSGIController.__call__ dispatches to the Controller method
        # the request is routed to. This routing information is
        # available in environ['pylons.routes_dict']    
        try:
            return WSGIController.__call__(self, environ, start_response)
        finally:
            model.Session.remove()

    def __after__(self, action, **params):
        self._stop_call_timing()
        self._write_call_timing()

    def _get_user(self, reference):
        return model.User.by_name(reference)

    def _get_pkg(self, reference):
        return model.Package.get(reference)

    def _get_harvest_source(self, reference):
        return model.HarvestSource.get(reference)

    def _get_request_data(self):
        try:
            request_data = request.params.keys()[0]
        except Exception, inst:
            msg = _("Can't find entity data in request params %s: %s") % (
                request.params.items(), str(inst)
            )
            raise ValueError, msg
        request_data = json.loads(request_data, encoding='utf8')
        if not isinstance(request_data, dict):
            raise ValueError, _("Request params must be in form of a json encoded dictionary.")
        # ensure unicode values
        for key, val in request_data.items():
            # if val is str then assume it is ascii, since json converts
            # utf8 encoded JSON to unicode
            request_data[key] = self._make_unicode(val)
        return request_data
        
    def _make_unicode(self, entity):
        if isinstance(entity, str):
            return unicode(entity)
        elif isinstance(entity, list):
            new_items = []
            for item in entity:
                new_items.append(self._make_unicode(item))
            return new_items
        elif isinstance(entity, dict):
            new_dict = {}
            for key, val in entity.items():
                new_dict[key] = self._make_unicode(val)
            return new_dict
        else:
            return entity

    def _get_user_for_apikey(self):
        apikey_header_name = config.get(APIKEY_HEADER_NAME_KEY, APIKEY_HEADER_NAME_DEFAULT)
        apikey = request.headers.get(apikey_header_name, '')
        if not apikey:
            apikey = request.environ.get(apikey_header_name, '')
        if not apikey:
            # For misunderstanding old documentation (now fixed).
            apikey = request.environ.get('HTTP_AUTHORIZATION', '')
        if not apikey:
            apikey = request.environ.get('Authorization', '')
            # Forget HTTP Auth credentials (they have spaces).
            if ' ' in apikey:
                apikey = ''
        if not apikey:
            return None
        self.log.debug("Received API Key: %s" % apikey)
        apikey = unicode(apikey)
        query = model.Session.query(model.User)
        user = query.filter_by(apikey=apikey).first()
        return user

    def _start_call_timing(self):
        c.time_call_started = self._get_now_time()

    def _stop_call_timing(self):
        c.time_call_stopped = self._get_now_time()
        
    def _write_call_timing(self):
        call_duration = c.time_call_stopped - c.time_call_started
        timing_data = {
            "path": request.path, 
            "started": c.time_call_started.isoformat(),
            "duration": str(call_duration),
        }
        timing_msg = json.dumps(timing_data)
        timing_cache_path = self._get_timing_cache_path()
        timing_file_path = os.path.join(timing_cache_path, c.time_call_started.isoformat())
        timing_file = file(timing_file_path, 'w')
        timing_file.write(timing_msg)
        timing_file.close()

    def _get_now_time(self):
        import datetime
        return datetime.datetime.now()

    def _get_timing_cache_path(self):
        path = os.path.join(config['pylons.cache_dir'], 'call_timing')
        if not os.path.exists(path):
             os.makedirs(path)
        return path



# Include the '_' function in the public names
__all__ = [__name for __name in locals().keys() if not __name.startswith('_') \
           or __name == '_']
