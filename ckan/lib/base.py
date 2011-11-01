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
from pylons.controllers.util import redirect_to, redirect
from pylons.decorators import jsonify, validate
from pylons.i18n import _, ungettext, N_, gettext
from pylons.templating import cached_template, pylons_globals
from genshi.template import MarkupTemplate
from webhelpers.html import literal

import ckan
from ckan import authz
from ckan.lib import i18n
import ckan.lib.helpers as h
from ckan.plugins import PluginImplementations, IGenshiStreamFilter
from ckan.lib.helpers import json
import ckan.model as model
from ckan.lib.cache import etag_cache

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
    # #1267 Convert detail to plain text, since WebOb 0.9.7.1 (which comes
    # with Lucid) causes an exception when unicode is received.
    detail = detail.encode('utf8')
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
        
        return literal(stream.render(method=method, encoding=None, strip_whitespace=False))
    
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
    authorizer = authz.Authorizer()
    log = logging.getLogger(__name__)

    def __before__(self, action, **params):
        c.__version__ = ckan.__version__
        self._identify_user()
        i18n.handle_request(request, c)

    def _identify_user(self):
        # see if it was proxied first
        c.remote_addr = request.environ.get('HTTP_X_FORWARDED_FOR', '')
        if not c.remote_addr:
            c.remote_addr = request.environ.get('REMOTE_ADDR', 'Unknown IP Address')

        # what is different between session['user'] and environ['REMOTE_USER']
        c.user = request.environ.get('REMOTE_USER', '')
        if c.user:
            c.user = c.user.decode('utf8')
            c.userobj = model.User.by_name(c.user)
            if c.userobj is None:
                # This occurs when you are logged in with openid, clean db
                # and then restart i.e. only really for testers. There is no
                # user object, so even though repoze thinks you are logged in
                # and your cookie has ckan_display_name, we need to force user
                # to login again to get the User object.
                c.user = None
        else:
            c.userobj = self._get_user_for_apikey()
            if c.userobj is not None:
                c.user = c.userobj.name
        if c.user:
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
        self._set_cors()

    def _set_cors(self):
        response.headers['Access-Control-Allow-Origin'] = "*"
        response.headers['Access-Control-Allow-Methods'] = "POST, PUT, GET, DELETE"
        response.headers['Access-Control-Allow-Headers'] = "X-CKAN-API-KEY, Content-Type"

    def _get_user(self, reference):
        return model.User.by_name(reference)

    def _get_pkg(self, reference):
        return model.Package.get(reference)

    def _get_group(self, reference):
        return model.Group.get(reference)

    def _get_tag(self, reference):
        return model.Tag.get(reference)

    @classmethod
    def _get_request_data(cls):
        '''Returns a dictionary, extracted from a request. The request data is
        in POST data and formatted as a dictionary that has been
        JSON-encoded.

        If there is no data, None or "" is returned.
        ValueError will be raised if the data is not a JSON-formatted dict.

        This function is only used by the API, so no strings need to be
        translated.
        '''
        cls.log.debug('Retrieving request params: %r' % request.params)
        cls.log.debug('Retrieving request POST: %r' % request.POST)
        request_data = None
        if request.POST:
            try:
                request_data = request.POST.keys()
            except Exception, inst:
                msg = "Could not find the POST data: %r : %s" % \
                      (request.POST, inst)
                raise ValueError, msg
            request_data = request_data[0]
        else:
            try:
                request_data = request.body
            except Exception, inst:
                msg = "Could not extract request body data: %s" % \
                      (inst)
                raise ValueError, msg
            cls.log.debug('Retrieved request body: %r' % request.body)
            if not request_data:
                msg = "No request body data"
                raise ValueError, msg
        if request_data:
            try:
                request_data = json.loads(request_data, encoding='utf8')
            except ValueError, e:
                raise ValueError, 'Error parsing JSON data. ' \
                                    'Error: %r ' \
                                    'JSON (Decoded and re-encoded): %r' % \
                                    (e, request_data)
            if not isinstance(request_data, dict):
                raise ValueError, "Request params must be in form of a json encoded dictionary."
            # ensure unicode values
            for key, val in request_data.items():
                # if val is str then assume it is ascii, since json converts
                # utf8 encoded JSON to unicode
                request_data[key] = cls._make_unicode(val)
        cls.log.debug('Request data extracted: %r' % request_data)
        return request_data

    @classmethod
    def _make_unicode(cls, entity):
        """Cast bare strings and strings in lists or dicts to Unicode
        """
        if isinstance(entity, str):
            return unicode(entity)
        elif isinstance(entity, list):
            new_items = []
            for item in entity:
                new_items.append(cls._make_unicode(item))
            return new_items
        elif isinstance(entity, dict):
            new_dict = {}
            for key, val in entity.items():
                new_dict[key] = cls._make_unicode(val)
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

    def _handle_update_of_authz(self, current_uors, domain_object):
        # In the event of a post request, work out which of the four possible actions
        # is to be done, and do it before displaying the page
        if 'add' in request.POST:
            self._add_user_object_role('users', current_uors, domain_object)

        if 'authz_add' in request.POST:
            self._add_user_object_role('authz_groups', current_uors, domain_object)

        if 'save' in request.POST:
            self._update_user_object_roles('users', current_uors, domain_object)

        if 'authz_save' in request.POST:
            self._update_user_object_roles('authz_groups', current_uors, domain_object)

    def _prepare_authz_info_for_render(self, user_object_roles):
        # =================
        # Display the page

        # Find out all the possible roles. At the moment, any role can be
        # associated with any object, so that's easy:
        possible_roles = model.Role.get_all()


        # uniquify and sort
        users = sorted(list(set([uor.user.name for uor in user_object_roles if uor.user])))
        authz_groups = sorted(list(set([uor.authorized_group.name for uor in user_object_roles if uor.authorized_group])))

        # make a dictionary from (user, role) to True, False
        users_roles = [( uor.user.name, uor.role) for uor in user_object_roles if uor.user]
        user_role_dict={}
        for u in users:
            for r in possible_roles:
                if (u,r) in users_roles:
                    user_role_dict[(u,r)]=True
                else:
                    user_role_dict[(u,r)]=False

        # and similarly make a dictionary from (authz_group, role) to True, False
        authz_groups_roles = [( uor.authorized_group.name, uor.role) for uor in user_object_roles if uor.authorized_group]
        authz_groups_role_dict={}
        for u in authz_groups:
            for r in possible_roles:
                if (u,r) in authz_groups_roles:
                    authz_groups_role_dict[(u,r)]=True
                else:
                    authz_groups_role_dict[(u,r)]=False

        c.roles = possible_roles
        c.users = users
        c.user_role_dict = user_role_dict
        c.authz_groups = authz_groups
        c.authz_groups_role_dict = authz_groups_role_dict

    def _update_user_object_roles(self, users_or_authz_groups, current_uors, domain_object):
        '''Update user object roles for this object.

        :param domain_object: the domain object for whom we are adding the user
        object role.
        '''
        # The permissions grid has been saved
        # which is a grid of checkboxes named user$role
        rpi = request.params.items()

        # The grid passes us a list of the users/roles that were displayed
        submitted = [ a for (a,b) in rpi if (b == u'submitted')]
        # and also those which were checked
        checked = [ a for (a,b) in rpi if (b == u'on')]

        # from which we can deduce true/false for each user/role combination
        # that was displayed in the form
        table_dict={}
        for a in submitted:
            table_dict[a]=False
        for a in checked:
            table_dict[a]=True

        # now we'll split up the user$role strings to make a dictionary from 
        # (user,role) to True/False, which tells us what we need to do.
        new_user_role_dict={}
        for (ur,val) in table_dict.items():
            u,r = ur.split('$')
            new_user_role_dict[(u,r)] = val
           
        if users_or_authz_groups=='users':
            current_users_roles = [( uor.user.name, uor.role) for uor in current_uors if uor.user]
        elif users_or_authz_groups=='authz_groups':
            current_users_roles = [( uor.authorized_group.name, uor.role) for uor in current_uors if uor.authorized_group]        
        else:
            assert False, "shouldn't be here"

        current_user_role_dict={}
        for (u,r) in current_users_roles:
            current_user_role_dict[(u,r)]=True

        # and now we can loop through our dictionary of desired states
        # checking whether a change needs to be made, and if so making it

        # Here we check whether someone is already assigned a role, in order
        # to avoid assigning it twice, or attempting to delete it when it
        # doesn't exist. Otherwise problems can occur.
        if users_or_authz_groups=='users':
            for ((u,r), val) in new_user_role_dict.items():
                if val:
                    if not ((u,r) in current_user_role_dict):
                        model.add_user_to_role(model.User.by_name(u),r,domain_object)
                else:
                    if ((u,r) in current_user_role_dict):
                        model.remove_user_from_role(model.User.by_name(u),r,domain_object)
        elif users_or_authz_groups=='authz_groups':
            for ((u,r), val) in new_user_role_dict.items():
                if val:
                    if not ((u,r) in current_user_role_dict):
                        model.add_authorization_group_to_role(model.AuthorizationGroup.by_name(u),r,domain_object)
                else:
                    if ((u,r) in current_user_role_dict):
                        model.remove_authorization_group_from_role(model.AuthorizationGroup.by_name(u),r,domain_object)
        else:
            assert False, "shouldn't be here"

        # finally commit the change to the database
        model.repo.commit_and_remove()
        h.flash_success("Changes Saved")

    # TODO: this repeats much of _update_user_object_roles
    def _add_user_object_role(self, users_or_authz_groups, current_uors, domain_object):
        '''
        current_uors: in order to avoid either creating a role twice or deleting one which is
        non-existent, we need to get the users' current roles (if any)
        '''
        # The user is attempting to set new roles for a named user
        new_user = request.params.get('new_user_name')
        # this is the list of roles whose boxes were ticked
        checked_roles = [ a for (a,b) in request.params.items() if (b == u'on')]
        # this is the list of all the roles that were in the submitted form
        submitted_roles = [ a for (a,b) in request.params.items() if (b == u'submitted')]

        # from this we can make a dictionary of the desired states
        # i.e. true for the ticked boxes, false for the unticked
        desired_roles = {}
        for r in submitted_roles:
            desired_roles[r]=False
        for r in checked_roles:
            desired_roles[r]=True

        if users_or_authz_groups=='users':
            current_roles = [uor.role for uor in current_uors if ( uor.user and uor.user.name == new_user )]
            user_object = model.User.by_name(new_user)
            if user_object==None:
                # The submitted user does not exist. Bail with flash message
                h.flash_error('unknown user:' + str (new_user))
            else:
                # Whenever our desired state is different from our current state, change it.
                for (r,val) in desired_roles.items():
                    if val:
                        if (r not in current_roles):
                            model.add_user_to_role(user_object, r,
                                    domain_object)
                    else:
                        if (r in current_roles):
                            model.remove_user_from_role(user_object, r,
                                    domain_object)
                h.flash_success("User Added")

        elif users_or_authz_groups=='authz_groups':
            current_roles = [uor.role for uor in current_uors if ( uor.authorized_group and uor.authorized_group.name == new_user )]
            user_object = model.AuthorizationGroup.by_name(new_user)
            if user_object==None:
                # The submitted user does not exist. Bail with flash message
                h.flash_error('unknown authorization group:' + str (new_user))
            else:
                # Whenever our desired state is different from our current state, change it.
                for (r,val) in desired_roles.items():
                    if val:
                        if (r not in current_roles):
                            model.add_authorization_group_to_role(user_object,
                                    r, domain_object)
                    else:
                        if (r in current_roles):
                            model.remove_authorization_group_from_role(user_object,
                                    r, domain_object)
                h.flash_success("Authorization Group Added")

        else:
            assert False, "shouldn't be here"

        # and finally commit all these changes to the database
        model.repo.commit_and_remove()


# Include the '_' function in the public names
__all__ = [__name for __name in locals().keys() if not __name.startswith('_') \
           or __name == '_']
