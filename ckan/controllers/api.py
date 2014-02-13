import os.path
import logging
import cgi
import datetime
import glob
import urllib

from webob.multidict import UnicodeMultiDict
from paste.util.multidict import MultiDict

import ckan.model as model
import ckan.logic as logic
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.search as search
import ckan.lib.navl.dictization_functions
import ckan.lib.jsonp as jsonp
import ckan.lib.munge as munge

from ckan.common import _, c, request, response


log = logging.getLogger(__name__)

# shortcuts
get_action = logic.get_action
NotAuthorized = logic.NotAuthorized
NotFound = logic.NotFound
ValidationError = logic.ValidationError
DataError = ckan.lib.navl.dictization_functions.DataError

IGNORE_FIELDS = ['q']
CONTENT_TYPES = {
    'text': 'text/plain;charset=utf-8',
    'html': 'text/html;charset=utf-8',
    'json': 'application/json;charset=utf-8',
}


class ApiController(base.BaseController):

    _actions = {}

    def __call__(self, environ, start_response):
        # we need to intercept and fix the api version
        # as it will have a "/" at the start
        routes_dict = environ['pylons.routes_dict']
        api_version = routes_dict.get('ver')
        if api_version:
            api_version = api_version[1:]
            routes_dict['ver'] = int(api_version)

        self._identify_user()
        try:
            context = {'model': model, 'user': c.user or c.author,
                       'auth_user_obj': c.userobj}
            logic.check_access('site_read', context)
        except NotAuthorized:
            response_msg = self._finish(403,
                                        _('Not authorized to see this page'))
            # Call start_response manually instead of the parent __call__
            # because we want to end the request instead of continuing.
            response_msg = response_msg.encode('utf8')
            body = '%i %s' % (response.status_int, response_msg)
            start_response(body, response.headers.items())
            return [response_msg]

        # avoid status_code_redirect intercepting error responses
        environ['pylons.status_code_redirect'] = True
        return base.BaseController.__call__(self, environ, start_response)

    def _finish(self, status_int, response_data=None,
                content_type='text'):
        '''When a controller method has completed, call this method
        to prepare the response.
        @return response message - return this value from the controller
                                   method
                 e.g. return self._finish(404, 'Package not found')
        '''
        assert(isinstance(status_int, int))
        response.status_int = status_int
        response_msg = ''
        if response_data is not None:
            response.headers['Content-Type'] = CONTENT_TYPES[content_type]
            if content_type == 'json':
                response_msg = h.json.dumps(response_data)
            else:
                response_msg = response_data
            # Support "JSONP" callback.
            if status_int == 200 and 'callback' in request.params and \
                (request.method == 'GET' or
                 c.logic_function and request.method == 'POST'):
                # escape callback to remove '<', '&', '>' chars
                callback = cgi.escape(request.params['callback'])
                response_msg = self._wrap_jsonp(callback, response_msg)
        return response_msg

    def _finish_ok(self, response_data=None,
                   content_type='json',
                   resource_location=None):
        '''If a controller method has completed successfully then
        calling this method will prepare the response.
        @param resource_location - specify this if a new
           resource has just been created.
        @return response message - return this value from the controller
                                   method
                                   e.g. return self._finish_ok(pkg_dict)
        '''
        if resource_location:
            status_int = 201
            self._set_response_header('Location', resource_location)
        else:
            status_int = 200

        return self._finish(status_int, response_data, content_type)

    def _finish_not_authz(self, extra_msg=None):
        response_data = _('Access denied')
        if extra_msg:
            response_data = '%s - %s' % (response_data, extra_msg)
        return self._finish(403, response_data, 'json')

    def _finish_not_found(self, extra_msg=None):
        response_data = _('Not found')
        if extra_msg:
            response_data = '%s - %s' % (response_data, extra_msg)
        return self._finish(404, response_data, 'json')

    def _finish_bad_request(self, extra_msg=None):
        response_data = _('Bad request')
        if extra_msg:
            response_data = '%s - %s' % (response_data, extra_msg)
        return self._finish(400, response_data, 'json')

    def _wrap_jsonp(self, callback, response_msg):
        return '%s(%s);' % (callback, response_msg)

    def _set_response_header(self, name, value):
        try:
            value = str(value)
        except Exception, inst:
            msg = "Couldn't convert '%s' header value '%s' to string: %s" % \
                (name, value, inst)
            raise Exception(msg)
        response.headers[name] = value

    def get_api(self, ver=None):
        response_data = {}
        response_data['version'] = ver
        return self._finish_ok(response_data)

    def snippet(self, snippet_path, ver=None):
        ''' Renders and returns a snippet used by ajax calls '''
        # we only allow snippets in templates/ajax_snippets and it's subdirs
        snippet_path = u'ajax_snippets/' + snippet_path
        return base.render(snippet_path, extra_vars=dict(request.params))

    def action(self, logic_function, ver=None):
        try:
            function = get_action(logic_function)
        except KeyError:
            log.error('Can\'t find logic function: %s' % logic_function)
            return self._finish_bad_request(
                _('Action name not known: %s') % logic_function)

        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'api_version': ver, 'auth_user_obj': c.userobj}
        model.Session()._context = context
        return_dict = {'help': function.__doc__}
        try:
            side_effect_free = getattr(function, 'side_effect_free', False)
            request_data = self._get_request_data(try_url_params=
                                                  side_effect_free)
        except ValueError, inst:
            log.error('Bad request data: %s' % inst)
            return self._finish_bad_request(
                _('JSON Error: %s') % inst)
        if not isinstance(request_data, dict):
            # this occurs if request_data is blank
            log.error('Bad request data - not dict: %r' % request_data)
            return self._finish_bad_request(
                _('Bad request data: %s') %
                'Request data JSON decoded to %r but '
                'it needs to be a dictionary.' % request_data)
        # if callback is specified we do not want to send that to the search
        if 'callback' in request_data:
            del request_data['callback']
        try:
            result = function(context, request_data)
            return_dict['success'] = True
            return_dict['result'] = result
        except DataError, e:
            log.error('Format incorrect: %s - %s' % (e.error, request_data))
            return_dict['error'] = {'__type': 'Integrity Error',
                                    'message': e.error,
                                    'data': request_data}
            return_dict['success'] = False
            return self._finish(400, return_dict, content_type='json')
        except NotAuthorized, e:
            return_dict['error'] = {'__type': 'Authorization Error',
                                    'message': _('Access denied')}
            return_dict['success'] = False
            
            if e.extra_msg:
                return_dict['error']['message'] += ': %s' % e.extra_msg

            return self._finish(403, return_dict, content_type='json')
        except NotFound, e:
            return_dict['error'] = {'__type': 'Not Found Error',
                                    'message': _('Not found')}
            if e.extra_msg:
                return_dict['error']['message'] += ': %s' % e.extra_msg
            return_dict['success'] = False
            return self._finish(404, return_dict, content_type='json')
        except ValidationError, e:
            error_dict = e.error_dict
            error_dict['__type'] = 'Validation Error'
            return_dict['error'] = error_dict
            return_dict['success'] = False
            # CS nasty_string ignore
            log.error('Validation error: %r' % str(e.error_dict))
            return self._finish(409, return_dict, content_type='json')
        except search.SearchQueryError, e:
            return_dict['error'] = {'__type': 'Search Query Error',
                                    'message': 'Search Query is invalid: %r' %
                                    e.args}
            return_dict['success'] = False
            return self._finish(400, return_dict, content_type='json')
        except search.SearchError, e:
            return_dict['error'] = {'__type': 'Search Error',
                                    'message': 'Search error: %r' % e.args}
            return_dict['success'] = False
            return self._finish(409, return_dict, content_type='json')
        except search.SearchIndexError, e:
            return_dict['error'] = {'__type': 'Search Index Error',
                    'message': 'Unable to add package to search index: %s' %
                    str(e)}
            return_dict['success'] = False
            return self._finish(500, return_dict, content_type='json')
        return self._finish_ok(return_dict)

    def _get_action_from_map(self, action_map, register, subregister):
        ''' Helper function to get the action function specified in
            the action map'''

        # translate old package calls to use dataset
        if register == 'package':
            register = 'dataset'

        action = action_map.get((register, subregister))
        if not action:
            action = action_map.get(register)
        if action:
            return get_action(action)

    def list(self, ver=None, register=None, subregister=None, id=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'api_version': ver,
                   'auth_user_obj': c.userobj}
        log.debug('listing: %s' % context)
        action_map = {
            'revision': 'revision_list',
            'group': 'group_list',
            'dataset': 'package_list',
            'tag': 'tag_list',
            'related': 'related_list',
            'licenses': 'license_list',
            ('dataset', 'relationships'): 'package_relationships_list',
            ('dataset', 'revisions'): 'package_revision_list',
            ('dataset', 'activity'): 'package_activity_list',
            ('group', 'activity'): 'group_activity_list',
            ('user', 'activity'): 'user_activity_list',
            ('user', 'dashboard_activity'): 'dashboard_activity_list',
            ('activity', 'details'): 'activity_detail_list',
        }

        action = self._get_action_from_map(action_map, register, subregister)
        if not action:
            return self._finish_bad_request(
                _('Cannot list entity of this type: %s') % register)
        try:
            return self._finish_ok(action(context, {'id': id}))
        except NotFound, e:
            extra_msg = e.extra_msg
            return self._finish_not_found(extra_msg)
        except NotAuthorized, e:
            extra_msg = e.extra_msg
            return self._finish_not_authz(extra_msg)

    def show(self, ver=None, register=None, subregister=None,
             id=None, id2=None):
        action_map = {
            'revision': 'revision_show',
            'group': 'group_show_rest',
            'tag': 'tag_show_rest',
            'related': 'related_show',
            'dataset': 'package_show_rest',
            ('dataset', 'relationships'): 'package_relationships_list',
        }
        for type in model.PackageRelationship.get_all_types():
            action_map[('dataset', type)] = 'package_relationships_list'

        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'api_version': ver, 'auth_user_obj': c.userobj}
        data_dict = {'id': id, 'id2': id2, 'rel': subregister}

        log.debug('show: %s' % context)

        action = self._get_action_from_map(action_map, register, subregister)
        if not action:
            return self._finish_bad_request(
                _('Cannot read entity of this type: %s') % register)
        try:
            return self._finish_ok(action(context, data_dict))
        except NotFound, e:
            extra_msg = e.extra_msg
            return self._finish_not_found(extra_msg)
        except NotAuthorized, e:
            extra_msg = e.extra_msg
            return self._finish_not_authz(extra_msg)

    def _represent_package(self, package):
        return package.as_dict(ref_package_by=self.ref_package_by,
                               ref_group_by=self.ref_group_by)

    def create(self, ver=None, register=None, subregister=None,
               id=None, id2=None):

        action_map = {
            'group': 'group_create_rest',
            'dataset': 'package_create_rest',
            'rating': 'rating_create',
            'related': 'related_create',
            ('dataset', 'relationships'): 'package_relationship_create_rest',
        }
        for type in model.PackageRelationship.get_all_types():
            action_map[('dataset', type)] = 'package_relationship_create_rest'

        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'api_version': ver, 'auth_user_obj': c.userobj}
        log.debug('create: %s' % (context))
        try:
            request_data = self._get_request_data()
            data_dict = {'id': id, 'id2': id2, 'rel': subregister}
            data_dict.update(request_data)
        except ValueError, inst:
            return self._finish_bad_request(
                _('JSON Error: %s') % inst)

        action = self._get_action_from_map(action_map, register, subregister)
        if not action:
            return self._finish_bad_request(
                _('Cannot create new entity of this type: %s %s') %
                (register, subregister))

        try:
            response_data = action(context, data_dict)
            location = None
            if "id" in data_dict:
                location = str('%s/%s' % (request.path.replace('package',
                                                               'dataset'),
                                          data_dict.get("id")))
            return self._finish_ok(response_data,
                                   resource_location=location)
        except NotAuthorized, e:
            extra_msg = e.extra_msg
            return self._finish_not_authz(extra_msg)
        except NotFound, e:
            extra_msg = e.extra_msg
            return self._finish_not_found(extra_msg)
        except ValidationError, e:
            # CS: nasty_string ignore
            log.error('Validation error: %r' % str(e.error_dict))
            return self._finish(409, e.error_dict, content_type='json')
        except DataError, e:
            log.error('Format incorrect: %s - %s' % (e.error, request_data))
            error_dict = {
                'success': False,
                'error': {'__type': 'Integrity Error',
                                    'message': e.error,
                                    'data': request_data}}
            return self._finish(400, error_dict, content_type='json')
        except search.SearchIndexError:
            log.error('Unable to add package to search index: %s' %
                      request_data)
            return self._finish(500,
                                _(u'Unable to add package to search index') %
                                request_data)
        except:
            model.Session.rollback()
            raise

    def update(self, ver=None, register=None, subregister=None,
               id=None, id2=None):
        action_map = {
            'dataset': 'package_update_rest',
            'group': 'group_update_rest',
            ('dataset', 'relationships'): 'package_relationship_update_rest',
        }
        for type in model.PackageRelationship.get_all_types():
            action_map[('dataset', type)] = 'package_relationship_update_rest'

        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'api_version': ver, 'id': id, 'auth_user_obj': c.userobj}
        log.debug('update: %s' % (context))
        try:
            request_data = self._get_request_data()
            data_dict = {'id': id, 'id2': id2, 'rel': subregister}
            data_dict.update(request_data)
        except ValueError, inst:
            return self._finish_bad_request(
                _('JSON Error: %s') % inst)

        action = self._get_action_from_map(action_map, register, subregister)
        if not action:
            return self._finish_bad_request(
                _('Cannot update entity of this type: %s') %
                register.encode('utf-8'))
        try:
            response_data = action(context, data_dict)
            return self._finish_ok(response_data)
        except NotAuthorized, e:
            extra_msg = e.extra_msg
            return self._finish_not_authz(extra_msg)
        except NotFound, e:
            extra_msg = e.extra_msg
            return self._finish_not_found(extra_msg)
        except ValidationError, e:
            # CS: nasty_string ignore
            log.error('Validation error: %r' % str(e.error_dict))
            return self._finish(409, e.error_dict, content_type='json')
        except DataError, e:
            log.error('Format incorrect: %s - %s' % (e.error, request_data))
            error_dict = {
                'success': False,
                'error': {'__type': 'Integrity Error',
                                    'message': e.error,
                                    'data': request_data}}
            return self._finish(400, error_dict, content_type='json')
        except search.SearchIndexError:
            log.error('Unable to update search index: %s' % request_data)
            return self._finish(500, _(u'Unable to update search index') %
                                request_data)

    def delete(self, ver=None, register=None, subregister=None,
               id=None, id2=None):
        action_map = {
            'group': 'group_delete',
            'dataset': 'package_delete',
            'related': 'related_delete',
            ('dataset', 'relationships'): 'package_relationship_delete_rest',
        }
        for type in model.PackageRelationship.get_all_types():
            action_map[('dataset', type)] = 'package_relationship_delete_rest'

        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'api_version': ver, 'auth_user_obj': c.userobj}

        data_dict = {'id': id, 'id2': id2, 'rel': subregister}

        log.debug('delete %s/%s/%s/%s' % (register, id, subregister, id2))

        action = self._get_action_from_map(action_map, register, subregister)
        if not action:
            return self._finish_bad_request(
                _('Cannot delete entity of this type: %s %s') %
                (register, subregister or ''))
        try:
            response_data = action(context, data_dict)
            return self._finish_ok(response_data)
        except NotAuthorized, e:
            extra_msg = e.extra_msg
            return self._finish_not_authz(extra_msg)
        except NotFound, e:
            extra_msg = e.extra_msg
            return self._finish_not_found(extra_msg)
        except ValidationError, e:
            # CS: nasty_string ignore
            log.error('Validation error: %r' % str(e.error_dict))
            return self._finish(409, e.error_dict, content_type='json')

    def search(self, ver=None, register=None):

        log.debug('search %s params: %r' % (register, request.params))
        if register == 'revision':
            since_time = None
            if 'since_id' in request.params:
                id = request.params['since_id']
                if not id:
                    return self._finish_bad_request(
                        _(u'No revision specified'))
                rev = model.Session.query(model.Revision).get(id)
                if rev is None:
                    return self._finish_not_found(
                        _(u'There is no revision with id: %s') % id)
                since_time = rev.timestamp
            elif 'since_time' in request.params:
                since_time_str = request.params['since_time']
                try:
                    since_time = h.date_str_to_datetime(since_time_str)
                except ValueError, inst:
                    return self._finish_bad_request('ValueError: %s' % inst)
            else:
                return self._finish_bad_request(
                    _("Missing search term ('since_id=UUID' or " +
                            " 'since_time=TIMESTAMP')"))
            revs = model.Session.query(model.Revision).\
                filter(model.Revision.timestamp > since_time)
            return self._finish_ok([rev.id for rev in revs])
        elif register in ['dataset', 'package', 'resource']:
            try:
                params = MultiDict(self._get_search_params(request.params))
            except ValueError, e:
                return self._finish_bad_request(
                    _('Could not read parameters: %r' % e))

            # if using API v2, default to returning the package ID if
            # no field list is specified
            if register in ['dataset', 'package'] and not params.get('fl'):
                params['fl'] = 'id' if ver == 2 else 'name'

            try:
                if register == 'resource':
                    query = search.query_for(model.Resource)

                    # resource search still uses ckan query parser
                    options = search.QueryOptions()
                    for k, v in params.items():
                        if (k in search.DEFAULT_OPTIONS.keys()):
                            options[k] = v
                    options.update(params)
                    options.username = c.user
                    options.search_tags = False
                    options.return_objects = False
                    query_fields = MultiDict()
                    for field, value in params.items():
                        field = field.strip()
                        if field in search.DEFAULT_OPTIONS.keys() or \
                                field in IGNORE_FIELDS:
                            continue
                        values = [value]
                        if isinstance(value, list):
                            values = value
                        for v in values:
                            query_fields.add(field, v)

                    results = query.run(
                        query=params.get('q'),
                        fields=query_fields,
                        options=options
                    )
                else:
                    # For package searches in API v3 and higher, we can pass
                    # parameters straight to Solr.
                    if ver in [1, 2]:
                        # Otherwise, put all unrecognised ones into the q
                        # parameter
                        params = search.\
                            convert_legacy_parameters_to_solr(params)
                    query = search.query_for(model.Package)

                    # Remove any existing fq param and set the capacity to
                    # public
                    if 'fq' in params:
                        del params['fq']
                    params['fq'] = '+capacity:public'
                    # if callback is specified we do not want to send that to
                    # the search
                    if 'callback' in params:
                        del params['callback']
                    results = query.run(params)
                return self._finish_ok(results)
            except search.SearchError, e:
                log.exception(e)
                return self._finish_bad_request(
                    _('Bad search option: %s') % e)
        else:
            return self._finish_not_found(
                _('Unknown register: %s') % register)

    @classmethod
    def _get_search_params(cls, request_params):
        if 'qjson' in request_params:
            try:
                qjson_param = request_params['qjson'].replace('\\\\u', '\\u')
                params = h.json.loads(qjson_param, encoding='utf8')
            except ValueError, e:
                raise ValueError(_('Malformed qjson value: %r')
                                 % e)
        elif len(request_params) == 1 and \
            len(request_params.values()[0]) < 2 and \
                request_params.keys()[0].startswith('{'):
            # e.g. {some-json}='1' or {some-json}=''
            params = h.json.loads(request_params.keys()[0], encoding='utf8')
        else:
            params = request_params
        if not isinstance(params, (UnicodeMultiDict, dict)):
            msg = _('Request params must be in form ' +
                    'of a json encoded dictionary.')
            raise ValueError(msg)
        return params

    def markdown(self, ver=None):
        raw_markdown = request.params.get('q', '')
        results = h.render_markdown(raw_markdown)

        return self._finish_ok(results)

    def tag_counts(self, ver=None):
        c.q = request.params.get('q', '')

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj}

        tag_names = get_action('tag_list')(context, {})
        results = []
        for tag_name in tag_names:
            tag_count = len(context['model'].Tag.get(tag_name).packages)
            results.append((tag_name, tag_count))
        return self._finish_ok(results)

    def throughput(self, ver=None):
        qos = self._calc_throughput()
        qos = str(qos)
        return self._finish_ok(qos)

    def _calc_throughput(self, ver=None):
        period = 10  # Seconds.
        timing_cache_path = self._get_timing_cache_path()
        call_count = 0
        for t in range(0, period):
            expr = '%s/%s*' % (
                timing_cache_path,
                (datetime.datetime.now() -
                 datetime.timedelta(0, t)).isoformat()[0:19],
            )
            call_count += len(glob.glob(expr))
        # Todo: Clear old records.
        return float(call_count) / period

    @jsonp.jsonpify
    def user_autocomplete(self):
        q = request.params.get('q', '')
        limit = request.params.get('limit', 20)
        user_list = []
        if q:
            context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author, 'auth_user_obj': c.userobj}

            data_dict = {'q': q, 'limit': limit}

            user_list = get_action('user_autocomplete')(context, data_dict)
        return user_list

    @jsonp.jsonpify
    def group_autocomplete(self):
        q = request.params.get('q', '')
        t = request.params.get('type', None)
        limit = request.params.get('limit', 20)
        try:
            limit = int(limit)
        except:
            limit = 20
        limit = min(50, limit)

        query = model.Group.search_by_name_or_title(q, t)

        def convert_to_dict(user):
            out = {}
            for k in ['id', 'name', 'title']:
                out[k] = getattr(user, k)
            return out

        query = query.limit(limit)
        out = map(convert_to_dict, query.all())
        return out

    def is_slug_valid(self):

        def package_exists(val):
            if model.Session.query(model.Package) \
                .autoflush(False).filter_by(name=val).count():
                return True
            return False

        def group_exists(val):
            if model.Session.query(model.Group) \
                    .autoflush(False).filter_by(name=val).count():
                return True
            return False

        slug = request.params.get('slug') or ''
        slugtype = request.params.get('type') or ''
        # TODO: We need plugins to be able to register new disallowed names
        disallowed = ['new', 'edit', 'search']
        if slugtype == u'package':
            response_data = dict(valid=not (package_exists(slug)
                                 or slug in disallowed))
            return self._finish_ok(response_data)
        if slugtype == u'group':
            response_data = dict(valid=not (group_exists(slug) or
                                 slug in disallowed))
            return self._finish_ok(response_data)
        return self._finish_bad_request('Bad slug type: %s' % slugtype)

    def dataset_autocomplete(self):
        q = request.params.get('incomplete', '')
        limit = request.params.get('limit', 10)
        package_dicts = []
        if q:
            context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author, 'auth_user_obj': c.userobj}

            data_dict = {'q': q, 'limit': limit}

            package_dicts = get_action('package_autocomplete')(context,
                                                               data_dict)

        resultSet = {'ResultSet': {'Result': package_dicts}}
        return self._finish_ok(resultSet)

    def tag_autocomplete(self):
        q = request.params.get('incomplete', '')
        limit = request.params.get('limit', 10)
        tag_names = []
        if q:
            context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author, 'auth_user_obj': c.userobj}

            data_dict = {'q': q, 'limit': limit}

            tag_names = get_action('tag_autocomplete')(context, data_dict)

        resultSet = {
            'ResultSet': {
                'Result': [{'Name': tag} for tag in tag_names]
            }
        }
        return self._finish_ok(resultSet)

    def format_autocomplete(self):
        q = request.params.get('incomplete', '')
        limit = request.params.get('limit', 5)
        formats = []
        if q:
            context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author, 'auth_user_obj': c.userobj}
            data_dict = {'q': q, 'limit': limit}
            formats = get_action('format_autocomplete')(context, data_dict)

        resultSet = {
            'ResultSet': {
                'Result': [{'Format': format} for format in formats]
            }
        }
        return self._finish_ok(resultSet)

    def munge_package_name(self):
        name = request.params.get('name')
        munged_name = munge.munge_name(name)
        return self._finish_ok(munged_name)

    def munge_title_to_package_name(self):
        name = request.params.get('title') or request.params.get('name')
        munged_name = munge.munge_title_to_name(name)
        return self._finish_ok(munged_name)

    def munge_tag(self):
        tag = request.params.get('tag') or request.params.get('name')
        munged_tag = munge.munge_tag(tag)
        return self._finish_ok(munged_tag)

    def format_icon(self):
        f = request.params.get('format')
        out = {
            'format': f,
            'icon': h.icon_url(h.format_icon(f))
        }
        return self._finish_ok(out)

    def status(self):
        context = {'model': model, 'session': model.Session}
        data_dict = {}
        status = get_action('status_show')(context, data_dict)
        return self._finish_ok(status)

    def i18n_js_translations(self, lang):
        ''' translation strings for front end '''
        ckan_path = os.path.join(os.path.dirname(__file__), '..')
        source = os.path.abspath(os.path.join(ckan_path, 'public',
                                 'base', 'i18n', '%s.js' % lang))
        response.headers['Content-Type'] = CONTENT_TYPES['json']
        if not os.path.exists(source):
            return '{}'
        f = open(source, 'r')
        return(f)

    @classmethod
    def _get_request_data(cls, try_url_params=False):
        '''Returns a dictionary, extracted from a request.

        If there is no data, None or "" is returned.
        ValueError will be raised if the data is not a JSON-formatted dict.

        The data is retrieved as a JSON-encoded dictionary from the request
        body.  Or, if the `try_url_params` argument is True and the request is
        a GET request, then an attempt is made to read the data from the url
        parameters of the request.

        try_url_params
            If try_url_params is False, then the data_dict is read from the
            request body.

            If try_url_params is True and the request is a GET request then the
            data is read from the url parameters.  The resulting dict will only
            be 1 level deep, with the url-param fields being the keys.  If a
            single key has more than one value specified, then the value will
            be a list of strings, otherwise just a string.

        '''
        def make_unicode(entity):
            '''Cast bare strings and strings in lists or dicts to Unicode. '''
            if isinstance(entity, str):
                return unicode(entity)
            elif isinstance(entity, list):
                new_items = []
                for item in entity:
                    new_items.append(make_unicode(item))
                return new_items
            elif isinstance(entity, dict):
                new_dict = {}
                for key, val in entity.items():
                    new_dict[key] = make_unicode(val)
                return new_dict
            else:
                return entity

        cls.log.debug('Retrieving request params: %r' % request.params)
        cls.log.debug('Retrieving request POST: %r' % request.POST)
        cls.log.debug('Retrieving request GET: %r' % request.GET)
        request_data = None
        if request.POST and request.content_type == 'multipart/form-data':
            request_data = dict(request.POST)
        elif request.POST:
            try:
                keys = request.POST.keys()
                # Parsing breaks if there is a = in the value, so for now
                # we will check if the data is actually all in a single key
                if keys and request.POST[keys[0]] in [u'1', u'']:
                    request_data = keys[0]
                else:
                    request_data = urllib.unquote_plus(request.body)
            except Exception, inst:
                msg = "Could not find the POST data: %r : %s" % \
                      (request.POST, inst)
                raise ValueError(msg)

        elif try_url_params and request.GET:
            return request.GET.mixed()

        else:
            try:
                if request.method in ['POST', 'PUT']:
                    request_data = request.body
                else:
                    request_data = None
            except Exception, inst:
                msg = "Could not extract request body data: %s" % \
                      (inst)
                raise ValueError(msg)
            cls.log.debug('Retrieved request body: %r' % request.body)
            if not request_data:
                if not try_url_params:
                    msg = "No request body data"
                    raise ValueError(msg)
                else:
                    request_data = {}
        if request_data and request.content_type != 'multipart/form-data':
            try:
                request_data = h.json.loads(request_data, encoding='utf8')
            except ValueError, e:
                raise ValueError('Error decoding JSON data. '
                                 'Error: %r '
                                 'JSON data extracted from the request: %r' %
                                 (e, request_data))
            if not isinstance(request_data, dict):
                raise ValueError('Request data JSON decoded to %r but '
                                 'it needs to be a dictionary.' % request_data)
            # ensure unicode values
            for key, val in request_data.items():
                # if val is str then assume it is ascii, since json converts
                # utf8 encoded JSON to unicode
                request_data[key] = make_unicode(val)
        cls.log.debug('Request data extracted: %r' % request_data)
        return request_data
