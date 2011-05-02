import logging

from paste.util.multidict import MultiDict 
from webob.multidict import UnicodeMultiDict

from ckan.lib.base import BaseController, response, c, _, gettext, request
from ckan.lib.helpers import json
import ckan.model as model
import ckan.rating
from ckan.lib.search import query_for, QueryOptions, SearchError, DEFAULT_OPTIONS
from ckan.plugins import PluginImplementations, IGroupController
from ckan.lib.munge import munge_title_to_name
from ckan.lib.navl.dictization_functions import DataError
import ckan.logic.action.get as get 
import ckan.logic.action.create as create
import ckan.logic.action.update as update
import ckan.logic.action.delete as delete
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.lib.jsonp import jsonpify
from ckan.forms.common import package_exists


log = logging.getLogger(__name__)

IGNORE_FIELDS = ['q']
CONTENT_TYPES = {
    'text': 'text/plain;charset=utf-8',
    'html': 'text/html;charset=utf-8',
    'json': 'application/json;charset=utf-8',
    }
class ApiController(BaseController):

    content_type_text = 'text/;charset=utf-8'
    content_type_html = 'text/html;charset=utf-8'
    content_type_json = 'application/json;charset=utf-8'

    def __call__(self, environ, start_response):
        self._identify_user()
        if not self.authorizer.am_authorized(c, model.Action.SITE_READ, model.System):
            response_msg = self._finish(403, _('Not authorized to see this page'))
            # Call start_response manually instead of the parent __call__
            # because we want to end the request instead of continuing.
            response_msg = response_msg.encode('utf8')
            body = '%i %s' % (response.status_int, response_msg)
            start_response(body, response.headers.items())
            return [response_msg]
        else:
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
                   request.method == 'GET':
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

    def list(self, ver=None, register=None, subregister=None, id=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'id': id, 'api_version': ver}
        log.debug('listing: %s' % context)
        action_map = {
            'revision': get.revision_list,
            'group': get.group_list,
            'package': get.package_list,
            'tag': get.tag_list,
            'licenses': get.licence_list,
            ('package', 'relationships'): get.package_relationships_list,
            ('package', 'revisions'): get.package_revision_list,
        }

        action = action_map.get((register, subregister)) 
        if not action:
            action = action_map.get(register)
        if not action:
            response.status_int = 400
            return gettext('Cannot list entity of this type: %s') % register
        try:
            return self._finish_ok(action(context))
        except NotFound, e:
            extra_msg = e.extra_msg
            return self._finish_not_found(extra_msg)
        except NotAuthorized:
            return self._finish_not_authz()

    def show(self, ver=None, register=None, subregister=None, id=None, id2=None):

        action_map = {
            'revision': get.revision_show,
            'group': get.group_show,
            'tag': get.tag_show,
            'package': get.package_show,
            ('package', 'relationships'): get.package_relationships_list,
        }

        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'id': id, 'id2': id2, 'rel': subregister,
                   'api_version': ver}
        for type in model.PackageRelationship.get_all_types():
            action_map[('package', type)] = get.package_relationships_list
        log.debug('show: %s' % context)

        action = action_map.get((register, subregister)) 
        if not action:
            action = action_map.get(register)
        if not action:
            response.status_int = 400
            return gettext('Cannot read entity of this type: %s') % register
        try:
            return self._finish_ok(action(context))
        except NotFound, e:
            extra_msg = e.extra_msg
            return self._finish_not_found(extra_msg)
        except NotAuthorized:
            return self._finish_not_authz()

    def _represent_package(self, package):
        return package.as_dict(ref_package_by=self.ref_package_by, ref_group_by=self.ref_group_by)

    def create(self, ver=None, register=None, subregister=None, id=None, id2=None):

        action_map = {
            ('package', 'relationships'): create.package_relationship_create,
             'group': create.group_create,
             'package': create.package_create_rest,
             'rating': create.rating_create,
        }
        for type in model.PackageRelationship.get_all_types():
            action_map[('package', type)] = create.package_relationship_create

        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'id': id, 'id2': id2, 'rel': subregister,
                   'api_version': ver}
        log.debug('create: %s' % (context))
        try:
            request_data = self._get_request_data()
        except ValueError, inst:
            response.status_int = 400
            return gettext('JSON Error: %s') % str(inst)

        action = action_map.get((register, subregister)) 
        if not action:
            action = action_map.get(register)
        if not action:
            response.status_int = 400
            return gettext('Cannot create new entity of this type: %s %s') % (register, subregister)
        try:
            response_data = action(request_data, context)
            location = None
            if "id" in context:
                location = str('%s/%s' % (request.path, context.get("id")))
            return self._finish_ok(response_data,
                                   resource_location=location)
        except NotAuthorized:
            return self._finish_not_authz()
        except ValidationError, e:
            log.error('Validation error: %r' % str(e.error_dict))
            return self._finish(409, e.error_dict, content_type='json')
        except DataError:
            log.error('Format incorrect: %s' % request_data)
            #TODO make better error message
            return self._finish(400, _(u'Integrity Error') % request_data)
        except:
            model.Session.rollback()
            raise
            
    def update(self, ver=None, register=None, subregister=None, id=None, id2=None):

        action_map = {
            ('package', 'relationships'): update.package_relationship_update,
             'package': update.package_update_rest,
             'group': update.group_update_rest,
        }
        for type in model.PackageRelationship.get_all_types():
            action_map[('package', type)] = update.package_relationship_update

        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'id': id, 'id2': id2, 'rel': subregister,
                   'api_version': ver}
        log.debug('update: %s' % (context))
        try:
            request_data = self._get_request_data()
        except ValueError, inst:
            response.status_int = 400
            return gettext('JSON Error: %s') % str(inst)
        action = action_map.get((register, subregister)) 
        if not action:
            action = action_map.get(register)
        if not action:
            response.status_int = 400
            return gettext('Cannot update entity of this type: %s') % register
        try:
            response_data = action(request_data, context)
            return self._finish_ok(response_data)
        except NotAuthorized:
            return self._finish_not_authz()
        except NotFound, e:
            extra_msg = e.extra_msg
            return self._finish_not_found(extra_msg)
        except ValidationError, e:
            log.error('Validation error: %r' % str(e.error_dict))
            return self._finish(409, e.error_dict, content_type='json')
        except DataError:
            log.error('Format incorrect: %s' % request_data)
            #TODO make better error message
            return self._finish(400, _(u'Integrity Error') % request_data)

    def delete(self, ver=None, register=None, subregister=None, id=None, id2=None):
        action_map = {
            ('package', 'relationships'): delete.package_relationship_delete,
             'group': delete.group_delete,
             'package': delete.package_delete,
        }
        for type in model.PackageRelationship.get_all_types():
            action_map[('package', type)] = delete.package_relationship_delete

        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'id': id, 'id2': id2, 'rel': subregister,
                   'api_version': ver}
        log.debug('delete %s/%s/%s/%s' % (register, id, subregister, id2))

        action = action_map.get((register, subregister)) 
        if not action:
            action = action_map.get(register)
        if not action:
            response.status_int = 400
            return gettext('Cannot delete entity of this type: %s %s') % (register, subregister or '')
        try:
            response_data = action(context)
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
        if register == 'revision':
            since_time = None
            if request.params.has_key('since_id'):
                id = request.params['since_id']
                rev = model.Session.query(model.Revision).get(id)
                if rev is None:
                    response.status_int = 400
                    return gettext(u'There is no revision with id: %s') % id
                since_time = rev.timestamp
            elif request.params.has_key('since_time'):
                since_time_str = request.params['since_time']
                try:
                    since_time = model.strptimestamp(since_time_str)
                except ValueError, inst:
                    response.status_int = 400
                    return 'ValueError: %s' % inst
            else:
                response.status_int = 400
                return gettext("Missing search term ('since_id=UUID' or 'since_time=TIMESTAMP')")
            revs = model.Session.query(model.Revision).filter(model.Revision.timestamp>since_time)
            return self._finish_ok([rev.id for rev in revs])
        elif register == 'package' or register == 'resource':
            try:
                params = self._get_search_params(request.params)
            except ValueError, e:
                response.status_int = 400
                return gettext('Could not read parameters: %r' % e)
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
            
            if register == 'package':
                options.ref_entity_with_attr = 'id' if ver == '2' else 'name'
            try:
                backend = None
                if register == 'resource': 
                    query = query_for(model.Resource, backend='sql')
                else:
                    query = query_for(model.Package)
                results = query.run(query=params.get('q'), 
                                    fields=query_fields, 
                                    options=options)
                return self._finish_ok(results)
            except SearchError, e:
                log.exception(e)
                response.status_int = 400
                return gettext('Bad search option: %s') % e
        else:
            response.status_int = 404
            return gettext('Unknown register: %s') % register

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

    def tag_counts(self, ver=None):
        log.debug('tag counts')
        tags = model.Session.query(model.Tag).all()
        results = []
        for tag in tags:
            tag_count = len(tag.package_tags)
            results.append((tag.name, tag_count))
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
        try:
            limit = int(limit)
        except:
            limit = 20
        limit = min(50, limit)
    
        query = model.User.search(q)
        def convert_to_dict(user):
            out = {}
            for k in ['id', 'name', 'fullname']:
                out[k] = getattr(user, k)
            return out
        query = query.limit(limit)
        out = map(convert_to_dict, query.all())
        return out


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

    def create_slug(self):

        title = request.params.get('title') or ''
        name = munge_title_to_name(title)
        if package_exists(name):
            valid = False
        else:
            valid = True
        #response.content_type = 'application/javascript'
        response_data = dict(name=name.replace('_', '-'), valid=valid)
        return self._finish_ok(response_data)

    def tag_autocomplete(self):
        incomplete = request.params.get('incomplete', '')
        if incomplete:
            query = query_for('tag', backend='sql')
            query.run(query=incomplete,
                      return_objects=True,
                      limit=10,
                      username=c.user)
            tagNames = [t.name for t in query.results]
        else:
            tagNames = []
        resultSet = {
            "ResultSet": {
                "Result": []
            }
        }
        for tagName in tagNames[:10]:
            result = {
                "Name": tagName
            }
            resultSet["ResultSet"]["Result"].append(result)
        return self._finish_ok(resultSet)

