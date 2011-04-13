import logging

from paste.util.multidict import MultiDict 
from ckan.lib.base import BaseController, response, c, _, gettext, request
from ckan.lib.helpers import json
import ckan.model as model
import ckan.rating
from ckan.lib.search import query_for, QueryOptions, SearchError, DEFAULT_OPTIONS
from ckan.plugins import PluginImplementations, IGroupController
from ckan.lib.navl.dictization_functions import DataError
import ckan.logic.action.get as get 
import ckan.logic.action.create as create
import ckan.logic.action.update as update
import ckan.logic.action.delete as delete
from ckan.logic import NotFound, NotAuthorized, ValidationError


log = logging.getLogger(__name__)

IGNORE_FIELDS = ['q']
CONTENT_TYPES = {
    'text': 'text/plain;charset=utf-8',
    'html': 'text/html;charset=utf-8',
    'json': 'application/json;charset=utf-8',
    }
class BaseApiController(BaseController):

    api_version = ''
    ref_package_by = ''
    ref_group_by = ''
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

    @classmethod
    def _ref_package(cls, package):
        assert cls.ref_package_by in ['id', 'name']
        return getattr(package, cls.ref_package_by)

    @classmethod
    def _ref_group(cls, group):
        assert cls.ref_group_by in ['id', 'name']
        return getattr(group, cls.ref_group_by)

    @classmethod
    def _list_package_refs(cls, packages):
        return [getattr(p, cls.ref_package_by) for p in packages]

    @classmethod
    def _list_group_refs(cls, groups):
        return [getattr(p, cls.ref_group_by) for p in groups]

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
                   newly_created_resource_location=None):
        '''If a controller method has completed successfully then
        calling this method will prepare the response.
        @param newly_created_resource_location - specify this if a new
           resource has just been created.
        @return response message - return this value from the controller
                                   method
                                   e.g. return self._finish_ok(pkg_dict)
        '''
        if newly_created_resource_location:
            status_int = 201
            self._set_response_header('Location',
                                      newly_created_resource_location)
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

class ApiVersion1(BaseApiController):

    api_version = '1'
    ref_package_by = 'name'
    ref_group_by = 'name'


class ApiVersion2(BaseApiController):

    api_version = '2'
    ref_package_by = 'id'
    ref_group_by = 'id'


class BaseRestController(BaseApiController):

    def get_api(self):
        response_data = {}
        response_data['version'] = self.api_version
        return self._finish_ok(response_data) 

    def list(self, register, subregister=None, id=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'id': id, 'api_version': self.api_version}
        log.debug('listing: %s' % context)
        action_map = {
            'revision': get.revision_list,
            'group': get.group_list,
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

    def show(self, register, id, subregister=None, id2=None):

        action_map = {
            'revision': get.revision_show,
            'group': get.group_show,
            'tag': get.tag_show,
            ('package', 'relationships'): get.package_relationships_list,
        }

        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'id': id, 'id2': id2, 'rel': subregister,
                   'api_version': self.api_version}
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

    def create(self, register, id=None, subregister=None, id2=None):

        action_map = {
            ('package', 'relationships'): create.package_relationship_create,
             'group': create.group_create,
             'rating': create.rating_create,
        }
        for type in model.PackageRelationship.get_all_types():
            action_map[('package', type)] = create.package_relationship_create

        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'id': id, 'id2': id2, 'rel': subregister,
                   'api_version': self.api_version}
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
            if "id" in context:
                location = str('%s/%s' % (request.path, context.get("id")))
                response.headers['Location'] = location
                log.debug('Response headers: %r' % (response.headers))
            return self._finish_ok(response_data)
        except NotAuthorized:
            return self._finish_not_authz()
        except ValidationError, e:
            log.error('Validation error: %r' % str(e.error_dict))
            return self._finish(409, e.error_dict, content_type='json')
        except DataError:
            log.error('Format incorrect: %s' % request_data)
            #TODO make better error message
            return self._finish(409, _(u'Integrity Error') % request_data)
        except:
            model.Session.rollback()
            raise
            
    def update(self, register, id, subregister=None, id2=None):

        action_map = {
            ('package', 'relationships'): update.package_relationship_update,
             'group': update.group_update,
        }
        for type in model.PackageRelationship.get_all_types():
            action_map[('package', type)] = update.package_relationship_update

        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'id': id, 'id2': id2, 'rel': subregister,
                   'api_version': self.api_version}
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
            return self._finish(409, _(u'Integrity Error') % request_data)

    def delete(self, register, id, subregister=None, id2=None):
        action_map = {
            ('package', 'relationships'): delete.package_relationship_delete,
             'group': delete.group_delete,
        }
        for type in model.PackageRelationship.get_all_types():
            action_map[('package', type)] = delete.package_relationship_delete

        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'id': id, 'id2': id2, 'rel': subregister,
                   'api_version': self.api_version}
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

    def search(self, register=None):
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
            if request.params.has_key('qjson'):
                if not request.params['qjson']:
                    response.status_int = 400
                    return gettext('Blank qjson parameter')
                params = json.loads(request.params['qjson'])
            elif request.params.values() and request.params.values() != [u''] and request.params.values() != [u'1']:
                params = request.params
            else:
                try:
                    params = self._get_request_data()
                except ValueError, inst:
                    response.status_int = 400
                    return gettext(u'Search params: %s') % unicode(inst)
            
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
                options.ref_entity_with_attr = self.ref_package_by
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

    def tag_counts(self):
        log.debug('tag counts')
        tags = model.Session.query(model.Tag).all()
        results = []
        for tag in tags:
            tag_count = len(tag.package_tags)
            results.append((tag.name, tag_count))
        return self._finish_ok(results)

    def throughput(self):
        qos = self._calc_throughput()
        qos = str(qos)
        return self._finish_ok(qos)

    def _calc_throughput(self):
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



    def _check_access(self, entity, action):
        # Checks apikey is okay and user is authorized to do the specified
        # action on the specified package (or other entity).
        # If both args are None then just check the apikey corresponds
        # to a user.
        api_key = None
        # Todo: Remove unused 'isOk' variable.
        isOk = False

        self.rest_api_user = c.user
        log.debug('check access - user %r' % self.rest_api_user)
        
        if action and entity and not isinstance(entity, model.PackageRelationship):
            if action != model.Action.READ and self.rest_api_user in (model.PSEUDO_USER__VISITOR, ''):
                self.log.debug("Valid API key needed to make changes")
                response.status_int = 403
                response.headers['Content-Type'] = self.content_type_json
                return False                
            
            am_authz = ckan.authz.Authorizer().is_authorized(self.rest_api_user, action, entity)
            if not am_authz:
                self.log.debug("User is not authorized to %s %s" % (action, entity))
                response.status_int = 403
                response.headers['Content-Type'] = self.content_type_json
                return False
        elif not self.rest_api_user:
            self.log.debug("No valid API key provided.")
            response.status_int = 403
            response.headers['Content-Type'] = self.content_type_json
            return False
        self.log.debug("Access OK.")
        response.status_int = 200
        return True                


class RestController(ApiVersion1, BaseRestController):
    # Implements CKAN API Version 1.

    def _represent_package(self, package):
        msg_data = super(RestController, self)._represent_package(package)
        msg_data['download_url'] = package.resources[0].url if package.resources else ''
        return msg_data

