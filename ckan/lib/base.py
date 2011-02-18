"""The base Controller API

Provides the BaseController class for subclassing.
"""
from datetime import datetime
from hashlib import md5
import logging
import os

from paste.deploy.converters import asbool
from pylons import c, cache, config, g, request, response, session
from pylons.controllers import WSGIController
from pylons.controllers.util import abort as _abort
from pylons.controllers.util import etag_cache, redirect_to, redirect
from pylons.decorators import jsonify, validate
from pylons.i18n import _, ungettext, N_, gettext
from pylons.templating import cached_template, pylons_globals
from genshi.template import MarkupTemplate
from webhelpers.html import literal

import ckan
import ckan.lib.helpers as h
from ckan.plugins import PluginImplementations, IGenshiStreamFilter
from ckan.lib.helpers import json
import ckan.model as model

# nuke cache
#from pylons import cache
#cache.clear()

PAGINATE_ITEMS_PER_PAGE = 50

APIKEY_HEADER_NAME_KEY = 'apikey_header_name'
APIKEY_HEADER_NAME_DEFAULT = 'X-CKAN-API-Key'

ALLOWED_FIELDSET_PARAMS = ['package_form', 'restrict']

def abort(status_code=None, detail='', headers=None, comment=None):
    if detail:
        h.flash_error(detail)
    return _abort(status_code=status_code, 
                  detail=detail, 
                  headers=headers, 
                  comment=comment)

def render(template_name, extra_vars=None, cache_key=None, cache_type=None, 
           cache_expire=None, method='xhtml', loader_class=MarkupTemplate):
    
    def render_template():
        globs = extra_vars or {}
        globs.update(pylons_globals())
        globs['actions'] = model.Action
        template = globs['app_globals'].genshi_loader.load(template_name,
            cls=loader_class)
        stream = template.generate(**globs)
        
        for item in PluginImplementations(IGenshiStreamFilter):
            stream = item.filter(stream)
        
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
        c.time_call_started = datetime.now()

        # what is different between session['user'] and environ['REMOTE_USER']
        c.__version__ = ckan.__version__
        c.user = request.environ.get('REMOTE_USER', None)
        # see if it was proxied first
        c.remote_addr = request.environ.get('HTTP_X_FORWARDED_FOR', '')
        if not c.remote_addr:
            c.remote_addr = request.environ.get('REMOTE_ADDR', 'Unknown IP Address')
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
        c.time_call_stopped = datetime.now()
        self._write_call_timing()

    def _get_user(self, reference):
        return model.User.by_name(reference)

    def _get_pkg(self, reference):
        return model.Package.get(reference)

    def _get_harvest_source(self, reference):
        return model.HarvestSource.get(reference)

    def _get_request_data(self):
        self.log.debug('Retrieving request params: %r' % request.params)
        self.log.debug('Retrieving request POST: %r' % request.POST)
        try:
            request_data = request.POST.keys()[0]
        except Exception, inst:
            msg = _("Can't find entity data in request POST data %s: %s") % (
                request.POST, str(inst)
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
        self.log.debug('Request data extracted: %r' % request_data)
        return request_data
        
    def _make_unicode(self, entity):
        """Cast bare strings and strings in lists or dicts to Unicode
        """
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

    def _write_call_timing(self):
        if asbool(config.get('ckan.enable_call_timing', "False")):
            call_duration = c.time_call_stopped - c.time_call_started
            timing_data = {
                "path": request.path, 
                "started": c.time_call_started.isoformat(),
                "duration": str(call_duration),
            }
            timing_msg = json.dumps(timing_data)
            timing_file_path = os.path.join(timing_cache_path, c.time_call_started.isoformat())
            timing_file = file(timing_file_path, 'w')
            timing_file.write(timing_msg)
            timing_file.close()

    def _get_timing_cache_path(self):

        return path

    @classmethod
    def _get_user_editable_groups(cls): 
        if not hasattr(c, 'user'):
            c.user = model.PSEUDO_USER__VISITOR
        import ckan.authz # Todo: Move import to top of this file?
        groups = ckan.authz.Authorizer.authorized_query(c.user, model.Group, 
            action=model.Action.EDIT).all()
        return [g for g in groups if g.state==model.State.ACTIVE] 

    def _get_package_dict(self, *args, **kwds):
        import ckan.forms
        user_editable_groups = self._get_user_editable_groups()
        package_dict = ckan.forms.get_package_dict(
            user_editable_groups=user_editable_groups,
            *args, **kwds
        )
        return package_dict

    def _edit_package_dict(self, *args, **kwds):
        import ckan.forms
        return ckan.forms.edit_package_dict(*args, **kwds)

    @classmethod
    def _get_package_fieldset(cls, is_admin=False, **kwds):
        kwds.update(request.params)
        kwds['user_editable_groups'] = cls._get_user_editable_groups()
        kwds['is_admin'] = is_admin
        from ckan.forms import GetPackageFieldset
        return GetPackageFieldset(**kwds).fieldset

    def _get_standard_package_fieldset(self):
        import ckan.forms
        user_editable_groups = self._get_user_editable_groups()
        fieldset = ckan.forms.get_standard_fieldset(
            user_editable_groups=user_editable_groups
        )
        return fieldset


# Include the '_' function in the public names
__all__ = [__name for __name in locals().keys() if not __name.startswith('_') \
           or __name == '_']
