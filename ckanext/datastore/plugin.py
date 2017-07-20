# encoding: utf-8

import logging


import ckan.plugins as p
import ckan.logic as logic
import ckan.model as model
from ckan.model.core import State

import ckanext.datastore.helpers as datastore_helpers
import ckanext.datastore.logic.action as action
import ckanext.datastore.logic.auth as auth
import ckanext.datastore.interfaces as interfaces
from ckanext.datastore.backend import (
    DatastoreException,
    _parse_sort_clause,
    DatastoreBackend
)
from ckanext.datastore.backend.postgres import DatastorePostgresqlBackend

log = logging.getLogger(__name__)
_get_or_bust = logic.get_or_bust

DEFAULT_FORMATS = []

ValidationError = p.toolkit.ValidationError


class DatastorePlugin(p.SingletonPlugin):
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IConfigurer)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IResourceUrlChange)
    p.implements(p.IDomainObjectModification, inherit=True)
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IResourceController, inherit=True)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IForkObserver, inherit=True)
    p.implements(interfaces.IDatastore, inherit=True)
    p.implements(interfaces.IDatastoreBackend, inherit=True)

    legacy_mode = False
    resource_show_action = None

    def __new__(cls, *args, **kwargs):
        idatastore_extensions = p.PluginImplementations(interfaces.IDatastore)
        idatastore_extensions = idatastore_extensions.extensions()

        if idatastore_extensions and idatastore_extensions[0].__class__ != cls:
            msg = ('The "datastore" plugin must be the first IDatastore '
                   'plugin loaded. Change the order it is loaded in '
                   '"ckan.plugins" in your CKAN .ini file and try again.')
            raise DatastoreException(msg)

        return super(cls, cls).__new__(cls, *args, **kwargs)

    # IDatastoreBackend

    def register_backends(self):
        return {
            'postgresql': DatastorePostgresqlBackend,
            'postgres': DatastorePostgresqlBackend,
        }

    # IConfigurer

    def update_config(self, config):
        DatastoreBackend.register_backends()
        DatastoreBackend.set_active_backend(config)

        p.toolkit.add_template_directory(config, 'templates')
        self.backend = DatastoreBackend.get_active_backend()

    # IConfigurable

    def configure(self, config):
        self.config = config
        self.backend.configure(config)

        # Legacy mode means that we have no read url. Consequently sql search
        # is not available and permissions do not have to be changed. In
        # legacy mode, the datastore runs on PG prior to 9.0 (for
        # example 8.4).
        if hasattr(self.backend, 'is_legacy_mode'):
            self.legacy_mode = self.backend.is_legacy_mode(self.config)

    # IDomainObjectModification
    # IResourceUrlChange

    def notify(self, entity, operation=None):
        if not isinstance(entity, model.Package) or self.legacy_mode:
            return
        # if a resource is new, it cannot have a datastore resource, yet
        if operation == model.domain_object.DomainObjectOperation.changed:
            context = {'model': model, 'ignore_auth': True}
            if entity.private:
                func = p.toolkit.get_action('datastore_make_private')
            else:
                func = p.toolkit.get_action('datastore_make_public')
            for resource in entity.resources:
                try:
                    func(context, {
                        'connection_url': self.backend.write_url,
                        'resource_id': resource.id})
                except p.toolkit.ObjectNotFound:
                    pass

    # IActions

    def get_actions(self):
        actions = {
            'datastore_create': action.datastore_create,
            'datastore_upsert': action.datastore_upsert,
            'datastore_delete': action.datastore_delete,
            'datastore_search': action.datastore_search,
            'datastore_info': action.datastore_info,
            'datastore_function_create': action.datastore_function_create,
            'datastore_function_delete': action.datastore_function_delete,
            'datastore_run_triggers': action.datastore_run_triggers,
        }
        if not self.legacy_mode:
            if getattr(self.backend, 'enable_sql_search', False):
                # Only enable search_sql if the config does not disable it
                actions.update({
                    'datastore_search_sql': action.datastore_search_sql,
                })
            actions.update({
                'datastore_make_private': action.datastore_make_private,
                'datastore_make_public': action.datastore_make_public})
        return actions

    # IAuthFunctions

    def get_auth_functions(self):
        return {
            'datastore_create': auth.datastore_create,
            'datastore_upsert': auth.datastore_upsert,
            'datastore_delete': auth.datastore_delete,
            'datastore_info': auth.datastore_info,
            'datastore_search': auth.datastore_search,
            'datastore_search_sql': auth.datastore_search_sql,
            'datastore_change_permissions': auth.datastore_change_permissions,
            'datastore_function_create': auth.datastore_function_create,
            'datastore_function_delete': auth.datastore_function_delete,
            'datastore_run_triggers': auth.datastore_run_triggers,
        }

    # IRoutes

    def before_map(self, m):
        m.connect(
            '/datastore/dump/{resource_id}',
            controller='ckanext.datastore.controller:DatastoreController',
            action='dump')
        m.connect(
            'resource_dictionary', '/dataset/{id}/dictionary/{resource_id}',
            controller='ckanext.datastore.controller:DatastoreController',
            action='dictionary', ckan_icon='book')
        return m

    # IResourceController

    def before_show(self, resource_dict):
        # Modify the resource url of datastore resources so that
        # they link to the datastore dumps.
        if resource_dict.get('url_type') == 'datastore':
            resource_dict['url'] = p.toolkit.url_for(
                controller='ckanext.datastore.controller:DatastoreController',
                action='dump', resource_id=resource_dict['id'],
                qualified=True)

        if 'datastore_active' not in resource_dict:
            resource_dict[u'datastore_active'] = False

        return resource_dict

    def after_delete(self, context, resources):
        model = context['model']
        pkg = context['package']
        res_query = model.Session.query(model.Resource)
        query = res_query.filter(
            model.Resource.package_id == pkg.id,
            model.Resource.state == State.DELETED
        )
        deleted = [
            res for res in query.all()
            if res.extras.get('datastore_active') is True]

        for res in deleted:
            self.backend.delete(context, {
                'resource_id': res.id,
            })
            res.extras['datastore_active'] = False
            res_query.update(
                {'extras': res.extras}, synchronize_session=False)

    # IDatastore

    def datastore_validate(self, context, data_dict, fields_types):
        column_names = fields_types.keys()
        fields = data_dict.get('fields')
        if fields:
            data_dict['fields'] = list(set(fields) - set(column_names))

        filters = data_dict.get('filters', {})
        for key in filters.keys():
            if key in fields_types:
                del filters[key]

        q = data_dict.get('q')
        if q:
            if isinstance(q, basestring):
                del data_dict['q']
            elif isinstance(q, dict):
                for key in q.keys():
                    if key in fields_types and isinstance(q[key], basestring):
                        del q[key]

        language = data_dict.get('language')
        if language:
            if isinstance(language, basestring):
                del data_dict['language']

        plain = data_dict.get('plain')
        if plain:
            if isinstance(plain, bool):
                del data_dict['plain']

        distinct = data_dict.get('distinct')
        if distinct:
            if isinstance(distinct, bool):
                del data_dict['distinct']

        sort_clauses = data_dict.get('sort')
        if sort_clauses:
            invalid_clauses = [
                c for c in sort_clauses
                if not _parse_sort_clause(
                    c, fields_types
                )
            ]
            data_dict['sort'] = invalid_clauses

        limit = data_dict.get('limit')
        if limit:
            is_positive_int = datastore_helpers.validate_int(limit,
                                                             non_negative=True)
            is_all = isinstance(limit, basestring) and limit.lower() == 'all'
            if is_positive_int or is_all:
                del data_dict['limit']

        offset = data_dict.get('offset')
        if offset:
            is_positive_int = datastore_helpers.validate_int(offset,
                                                             non_negative=True)
            if is_positive_int:
                del data_dict['offset']

        return data_dict

    def datastore_delete(self, context, data_dict, fields_types, query_dict):
        hook = getattr(self.backend, 'datastore_delete', None)
        if hook:
            query_dict = hook(context, data_dict, fields_types, query_dict)
        return query_dict

    def datastore_search(self, context, data_dict, fields_types, query_dict):
        hook = getattr(self.backend, 'datastore_search', None)
        if hook:
            query_dict = hook(context, data_dict, fields_types, query_dict)
        return query_dict

    def get_helpers(self):
        return {
            'datastore_dictionary': datastore_helpers.datastore_dictionary}

    # IForkObserver

    def before_fork(self):
        try:
            before_fork = self.backend.before_fork
        except AttributeError:
            pass
        else:
            before_fork()
