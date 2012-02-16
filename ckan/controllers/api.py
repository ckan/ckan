import logging

from paste.util.multidict import MultiDict 
from webob.multidict import UnicodeMultiDict

from ckan.lib.base import BaseController, response, c, _, gettext, request
from ckan.lib.helpers import json, date_str_to_datetime
import ckan.model as model
import ckan.rating
from ckan.lib.search import (query_for, QueryOptions, SearchIndexError, SearchError,
                             SearchQueryError, DEFAULT_OPTIONS,
                             convert_legacy_parameters_to_solr)
from ckan.plugins import PluginImplementations, IGroupController
from ckan.lib.navl.dictization_functions import DataError
from ckan.lib.munge import munge_name, munge_title_to_name, munge_tag
from ckan.logic import get_action, check_access
from ckan.logic import NotFound, NotAuthorized, ValidationError, ParameterError
from ckan.lib.jsonp import jsonpify
from ckan.forms.common import package_exists, group_exists


log = logging.getLogger(__name__)

IGNORE_FIELDS = ['q']
CONTENT_TYPES = {
    'text': 'text/plain;charset=utf-8',
    'html': 'text/html;charset=utf-8',
    'json': 'application/json;charset=utf-8',
    }
class ApiController(BaseController):

    _actions = {}

    def __call__(self, environ, start_response):
        self._identify_user()
        try:
            context = {'model':model,'user': c.user or c.author}
            check_access('site_read',context)
        except NotAuthorized:
            response_msg = self._finish(403, _('Not authorized to see this page'))
            # Call start_response manually instead of the parent __call__
            # because we want to end the request instead of continuing.
            response_msg = response_msg.encode('utf8')
            body = '%i %s' % (response.status_int, response_msg)
            start_response(body, response.headers.items())
            return [response_msg]

        # avoid status_code_redirect intercepting error responses
        environ['pylons.status_code_redirect'] = True
        return BaseController.__call__(self, environ, start_response)

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
                response_msg = json.dumps(response_data)
            else:
                response_msg = response_data
            # Support "JSONP" callback.
            if status_int==200 and request.params.has_key('callback') and \
                   (request.method == 'GET' or \
                    c.logic_function and request.method == 'POST'):
                callback = request.params['callback']
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
            self._set_response_header('Location',
                                      resource_location)
        else:
            status_int = 200

        return self._finish(status_int, response_data,
                            content_type=content_type)

    def _finish_not_authz(self):
        response_data = _('Access denied')
        return self._finish(status_int=403,
                            response_data=response_data,
                            content_type='json')

    def _finish_not_found(self, extra_msg=None):
        response_data = _('Not found')
        if extra_msg:
            response_data = '%s - %s' % (response_data, extra_msg)
        return self._finish(status_int=404,
                            response_data=response_data,
                            content_type='json')

    def _finish_bad_request(self, extra_msg=None):
        response_data = _('Bad request')
        if extra_msg:
            response_data = '%s - %s' % (response_data, extra_msg)
        return self._finish(status_int=400,
                            response_data=response_data,
                            content_type='json')

    def _wrap_jsonp(self, callback, response_msg):
        return '%s(%s);' % (callback, response_msg)

    def _set_response_header(self, name, value):
        try:
            value = str(value)
        except Exception, inst:
            msg = "Couldn't convert '%s' header value '%s' to string: %s" % (name, value, inst)
            raise Exception, msg
        response.headers[name] = value

    def get_api(self, ver=None):
        response_data = {}
        response_data['version'] = ver or '1'
        return self._finish_ok(response_data) 
    
    def action(self, logic_function):
        function = get_action(logic_function)
        if not function:
            log.error('Can\'t find logic function: %s' % logic_function)
            return self._finish_bad_request(
                gettext('Action name not known: %s') % str(logic_function))
        
        context = {'model': model, 'session': model.Session, 'user': c.user}
        model.Session()._context = context
        return_dict = {'help': function.__doc__}
        try:
            request_data = self._get_request_data()
        except ValueError, inst:
            log.error('Bad request data: %s' % str(inst))
            return self._finish_bad_request(
                gettext('JSON Error: %s') % str(inst))
        if not isinstance(request_data, dict):
            # this occurs if request_data is blank
            log.error('Bad request data - not dict: %r' % request_data)
            return self._finish_bad_request(
                gettext('Bad request data: %s') % \
                'Request data JSON decoded to %r but ' \
                'it needs to be a dictionary.' % request_data)
        try:
            result = function(context, request_data)
            return_dict['success'] = True
            return_dict['result'] = result
        except DataError, e:
            log.error('Format incorrect: %s - %s' % (e.error, request_data))
            #TODO make better error message
            return self._finish(400, _(u'Integrity Error') + \
                                ': %s - %s' %  (e.error, request_data))
        except NotAuthorized:
            return_dict['error'] = {'__type': 'Authorization Error',
                                    'message': _('Access denied')}
            return_dict['success'] = False
            return self._finish(403, return_dict, content_type='json')
        except NotFound:
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
            log.error('Validation error: %r' % str(e.error_dict))
            return self._finish(409, return_dict, content_type='json')
        except ParameterError, e:
            return_dict['error'] = {'__type': 'Parameter Error',
                                    'message': '%s: %s' % \
                                    (_('Parameter Error'), e.extra_msg)}
            return_dict['success'] = False
            log.error('Parameter error: %r' % e.extra_msg)
            return self._finish(409, return_dict, content_type='json')            
        except SearchQueryError, e:
            return_dict['error'] = {'__type': 'Search Query Error',
                                    'message': 'Search Query is invalid: %r' % e.args }
            return_dict['success'] = False
            return self._finish(400, return_dict, content_type='json')        
        except SearchError, e:
            return_dict['error'] = {'__type': 'Search Error',
                                    'message': 'Search error: %r' % e.args }
            return_dict['success'] = False
            return self._finish(409, return_dict, content_type='json')        
        return self._finish_ok(return_dict)

    def list(self, ver=None, register=None, subregister=None, id=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'api_version': ver}
        log.debug('listing: %s' % context)
        action_map = {
            'revision': get_action('revision_list'),
            'group': get_action('group_list'),
            'dataset': get_action('package_list'),
            'package': get_action('package_list'),
            'tag': get_action('tag_list'),
            'licenses': get_action('licence_list'),
            ('dataset', 'relationships'): get_action('package_relationships_list'),
            ('package', 'relationships'): get_action('package_relationships_list'),
            ('dataset', 'revisions'): get_action('package_revision_list'),
            ('package', 'revisions'): get_action('package_revision_list'),
            ('package', 'activity'): get_action('package_activity_list'),
            ('dataset', 'activity'): get_action('package_activity_list'),
            ('group', 'activity'): get_action('group_activity_list'),
            ('user', 'activity'): get_action('user_activity_list'),
            ('activity', 'details'): get_action('activity_detail_list')
        }

        action = action_map.get((register, subregister)) 
        if not action:
            action = action_map.get(register)
        if not action:
            return self._finish_bad_request(
                gettext('Cannot list entity of this type: %s') % register)
        try:
            return self._finish_ok(action(context, {'id': id}))
        except NotFound, e:
            extra_msg = e.extra_msg
            return self._finish_not_found(extra_msg)
        except NotAuthorized:
            return self._finish_not_authz()

    def show(self, ver=None, register=None, subregister=None, id=None, id2=None):
        action_map = {
            'revision': get_action('revision_show'),
            'group': get_action('group_show_rest'),
            'tag': get_action('tag_show_rest'),
            'dataset': get_action('package_show_rest'),
            'package': get_action('package_show_rest'),
            ('dataset', 'relationships'): get_action('package_relationships_list'),
            ('package', 'relationships'): get_action('package_relationships_list'),
        }

        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'api_version': ver}
        data_dict = {'id': id, 'id2': id2, 'rel': subregister}

        for type in model.PackageRelationship.get_all_types():
            action_map[('dataset', type)] = get_action('package_relationships_list')
            action_map[('package', type)] = get_action('package_relationships_list')
        log.debug('show: %s' % context)

        action = action_map.get((register, subregister)) 
        if not action:
            action = action_map.get(register)
        if not action:
            return self._finish_bad_request(
                gettext('Cannot read entity of this type: %s') % register)
        try:
            
            return self._finish_ok(action(context, data_dict))
        except NotFound, e:
            extra_msg = e.extra_msg
            return self._finish_not_found(extra_msg)
        except NotAuthorized:
            return self._finish_not_authz()

    def _represent_package(self, package):
        return package.as_dict(ref_package_by=self.ref_package_by, ref_group_by=self.ref_group_by)

    def create(self, ver=None, register=None, subregister=None, id=None, id2=None):

        action_map = {
            ('dataset', 'relationships'): get_action('package_relationship_create_rest'),
            ('package', 'relationships'): get_action('package_relationship_create_rest'),
             'group': get_action('group_create_rest'),
             'dataset': get_action('package_create_rest'),
             'package': get_action('package_create_rest'),
             'rating': get_action('rating_create'),
        }

        for type in model.PackageRelationship.get_all_types():
            action_map[('dataset', type)] = get_action('package_relationship_create_rest')
            action_map[('package', type)] = get_action('package_relationship_create_rest')

        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'api_version': ver}
        log.debug('create: %s' % (context))
        try:
            request_data = self._get_request_data()
            data_dict = {'id': id, 'id2': id2, 'rel': subregister}
            data_dict.update(request_data)
        except ValueError, inst:
            return self._finish_bad_request(
                gettext('JSON Error: %s') % str(inst))

        action = action_map.get((register, subregister)) 
        if not action:
            action = action_map.get(register)
        if not action:
            return self._finish_bad_request(
                gettext('Cannot create new entity of this type: %s %s') % \
                (register, subregister))

        try:
            response_data = action(context, data_dict)
            location = None
            if "id" in data_dict:
                location = str('%s/%s' % (request.path.replace('package', 'dataset'),
                                          data_dict.get("id")))
            return self._finish_ok(response_data,
                                   resource_location=location)
        except NotAuthorized:
            return self._finish_not_authz()
        except NotFound, e:
            extra_msg = e.extra_msg
            return self._finish_not_found(extra_msg)
        except ValidationError, e:
            log.error('Validation error: %r' % str(e.error_dict))
            return self._finish(409, e.error_dict, content_type='json')
        except DataError, e:
            log.error('Format incorrect: %s - %s' % (e.error, request_data))
            #TODO make better error message
            return self._finish(400, _(u'Integrity Error') + \
                                ': %s - %s' %  (e.error, request_data))
        except SearchIndexError:
            log.error('Unable to add package to search index: %s' % request_data)
            return self._finish(500, _(u'Unable to add package to search index') % request_data)
        except:
            model.Session.rollback()
            raise
            
    def update(self, ver=None, register=None, subregister=None, id=None, id2=None):
        action_map = {
            ('dataset', 'relationships'): get_action('package_relationship_update_rest'),
            ('package', 'relationships'): get_action('package_relationship_update_rest'),
             'dataset': get_action('package_update_rest'),
             'package': get_action('package_update_rest'),
             'group': get_action('group_update_rest'),
        }
        for type in model.PackageRelationship.get_all_types():
            action_map[('dataset', type)] = get_action('package_relationship_update_rest')
            action_map[('package', type)] = get_action('package_relationship_update_rest')

        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'api_version': ver, 'id': id}
        log.debug('update: %s' % (context))
        try:
            request_data = self._get_request_data()
            data_dict = {'id': id, 'id2': id2, 'rel': subregister}
            data_dict.update(request_data)
        except ValueError, inst:
            return self._finish_bad_request(
                gettext('JSON Error: %s') % str(inst))
        action = action_map.get((register, subregister)) 
        if not action:
            action = action_map.get(register)
        if not action:
            return self._finish_bad_request(
                gettext('Cannot update entity of this type: %s') % \
                    register.encode('utf-8'))
        try:
            response_data = action(context, data_dict)
            return self._finish_ok(response_data)
        except NotAuthorized:
            return self._finish_not_authz()
        except NotFound, e:
            extra_msg = e.extra_msg
            return self._finish_not_found(extra_msg)
        except ValidationError, e:
            log.error('Validation error: %r' % str(e.error_dict))
            return self._finish(409, e.error_dict, content_type='json')
        except DataError, e:
            log.error('Format incorrect: %s - %s' % (e.error, request_data))
            #TODO make better error message
            return self._finish(400, _(u'Integrity Error') + \
                                ': %s - %s' %  (e.error, request_data))
        except SearchIndexError:
            log.error('Unable to update search index: %s' % request_data)
            return self._finish(500, _(u'Unable to update search index') % request_data)

    def delete(self, ver=None, register=None, subregister=None, id=None, id2=None):
        action_map = {
            ('dataset', 'relationships'): get_action('package_relationship_delete_rest'),
            ('package', 'relationships'): get_action('package_relationship_delete_rest'),
             'group': get_action('group_delete'),
             'dataset': get_action('package_delete'),
             'package': get_action('package_delete'),
        }
        for type in model.PackageRelationship.get_all_types():
            action_map[('dataset', type)] = get_action('package_relationship_delete_rest')
            action_map[('package', type)] = get_action('package_relationship_delete_rest')

        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'api_version': ver}

        data_dict = {'id': id, 'id2': id2, 'rel': subregister}

        log.debug('delete %s/%s/%s/%s' % (register, id, subregister, id2))

        action = action_map.get((register, subregister)) 
        if not action:
            action = action_map.get(register)
        if not action:
            return self._finish_bad_request(
                gettext('Cannot delete entity of this type: %s %s') %\
                (register, subregister or ''))
        try:
            response_data = action(context, data_dict)
            return self._finish_ok(response_data)
        except NotAuthorized:
            return self._finish_not_authz()
        except NotFound, e:
            extra_msg = e.extra_msg
            return self._finish_not_found(extra_msg)
        except ValidationError, e:
            log.error('Validation error: %r' % str(e.error_dict))
            return self._finish(409, e.error_dict, content_type='json')

    def search(self, ver=None, register=None):
        
        log.debug('search %s params: %r' % (register, request.params))
        ver = ver or '1' # i.e. default to v1
        if register == 'revision':
            since_time = None
            if request.params.has_key('since_id'):
                id = request.params['since_id']
                if not id:
                    return self._finish_bad_request(
                        gettext(u'No revision specified'))
                rev = model.Session.query(model.Revision).get(id)
                if rev is None:
                    return self._finish_not_found(
                        gettext(u'There is no revision with id: %s') % id)
                since_time = rev.timestamp
            elif request.params.has_key('since_time'):
                since_time_str = request.params['since_time']
                try:
                    since_time = date_str_to_datetime(since_time_str)
                except ValueError, inst:
                    return self._finish_bad_request('ValueError: %s' % inst)
            else:
                return self._finish_bad_request(
                    gettext("Missing search term ('since_id=UUID' or 'since_time=TIMESTAMP')"))
            revs = model.Session.query(model.Revision).filter(model.Revision.timestamp>since_time)
            return self._finish_ok([rev.id for rev in revs])
        elif register in ['dataset', 'package', 'resource']:
            try:
                params = MultiDict(self._get_search_params(request.params))
            except ValueError, e:
                return self._finish_bad_request(
                    gettext('Could not read parameters: %r' % e))

            # if using API v2, default to returning the package ID if
            # no field list is specified
            if register in ['dataset', 'package'] and not params.get('fl'):
                params['fl'] = 'id' if ver == '2' else 'name'

            try:
                if register == 'resource': 
                    query = query_for(model.Resource)

                    # resource search still uses ckan query parser
                    options = QueryOptions()
                    for k, v in params.items():
                        if (k in DEFAULT_OPTIONS.keys()):
                            options[k] = v
                    options.update(params)
                    options.username = c.user
                    options.search_tags = False
                    options.return_objects = False
                    query_fields = MultiDict()
                    for field, value in params.items():
                        field = field.strip()
                        if field in DEFAULT_OPTIONS.keys() or \
                           field in IGNORE_FIELDS:
                            continue
                        values = [value]
                        if isinstance(value, list):
                            values = value
                        for v in values:
                            query_fields.add(field, v)

                    results = query.run(
                        query=params.get('q'), fields=query_fields, options=options
                    )
                else:
                    # For package searches in API v3 and higher, we can pass
                    # parameters straight to Solr.
                    if ver in u'12':
                        # Otherwise, put all unrecognised ones into the q parameter
                        params = convert_legacy_parameters_to_solr(params)
                    query = query_for(model.Package)
                    results = query.run(params)
                return self._finish_ok(results)
            except SearchError, e:
                log.exception(e)
                return self._finish_bad_request(
                    gettext('Bad search option: %s') % e)
        else:
            return self._finish_not_found(
                gettext('Unknown register: %s') % register)

    @classmethod
    def _get_search_params(cls, request_params):
        if request_params.has_key('qjson'):
            try:
                params = json.loads(request_params['qjson'], encoding='utf8')
            except ValueError, e:
                raise ValueError, gettext('Malformed qjson value') + ': %r' % e
        elif len(request_params) == 1 and \
                 len(request_params.values()[0]) < 2 and \
                 request_params.keys()[0].startswith('{'):
            # e.g. {some-json}='1' or {some-json}=''
            params = json.loads(request_params.keys()[0], encoding='utf8')
        else:
            params = request_params
        if not isinstance(params, (UnicodeMultiDict, dict)):
            raise ValueError, _('Request params must be in form of a json encoded dictionary.')
        return params        

    def markdown(self, ver=None):
        raw_markdown = request.params.get('q', '')
        results = ckan.misc.MarkdownFormat().to_html(raw_markdown)

        return self._finish_ok(results)

    def tag_counts(self, ver=None):
        c.q = request.params.get('q', '')

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}

        data_dict = {'all_fields': True}

        tag_list = get_action('tag_list')(context, data_dict)
        results = []
        for tag in tag_list:
            tag_count = len(tag['packages'])
            results.append((tag['name'], tag_count))
        return self._finish_ok(results)

    def throughput(self, ver=None):
        qos = self._calc_throughput()
        qos = str(qos)
        return self._finish_ok(qos)

    def _calc_throughput(self, ver=None):
        period = 10  # Seconds.
        timing_cache_path = self._get_timing_cache_path()
        call_count = 0
        import datetime, glob
        for t in range(0, period):
            expr = '%s/%s*' % (
                timing_cache_path,
                (datetime.datetime.now() - datetime.timedelta(0,t)).isoformat()[0:19],
            )
            call_count += len(glob.glob(expr))
        # Todo: Clear old records.
        return float(call_count) / period

    @jsonpify
    def user_autocomplete(self):
        q = request.params.get('q', '')
        limit = request.params.get('limit', 20)
        user_list = []
        if q:
            context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author}

            data_dict = {'q':q,'limit':limit}

            user_list = get_action('user_autocomplete')(context,data_dict)
        return user_list


    @jsonpify
    def authorizationgroup_autocomplete(self):
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

    def is_slug_valid(self):
        slug = request.params.get('slug') or ''
        slugtype = request.params.get('type') or ''
        if slugtype==u'package':
            response_data = dict(valid=not bool(package_exists(slug)))
            return self._finish_ok(response_data)
        if slugtype==u'group':
            response_data = dict(valid=not bool(group_exists(slug)))
            return self._finish_ok(response_data)
        return self._finish_bad_request('Bad slug type: %s' % slugtype)
            

    def dataset_autocomplete(self):
        q = request.params.get('incomplete', '')
        q_lower = q.lower()
        limit = request.params.get('limit', 10)
        tag_names = []
        if q:
            context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author}

            data_dict = {'q': q, 'limit': limit}

            package_dicts = get_action('package_autocomplete')(context, data_dict)

        resultSet = {'ResultSet': {'Result': package_dicts}}
        return self._finish_ok(resultSet)

    def tag_autocomplete(self):
        q = request.params.get('incomplete', '')
        limit = request.params.get('limit', 10)
        tag_names = []
        if q:
            context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author}

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
                       'user': c.user or c.author}
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
        munged_name = munge_name(name)
        return self._finish_ok(munged_name)

    def munge_title_to_package_name(self):
        name = request.params.get('title') or request.params.get('name')
        munged_name = munge_title_to_name(name)
        return self._finish_ok(munged_name)        
        
    def munge_tag(self):
        tag = request.params.get('tag') or request.params.get('name')
        munged_tag = munge_tag(tag)
        return self._finish_ok(munged_tag)

    def status(self):
        context = {'model': model, 'session': model.Session}
        data_dict = {}
        status = get_action('status_show')(context, data_dict)
        return self._finish_ok(status)
