# encoding: utf-8

import logging


import ckan.plugins as p
import ckan.logic as logic
import ckan.model as model
import ckanext.datastore.logic.action as action
import ckanext.datastore.logic.auth as auth
import ckanext.datastore.interfaces as interfaces
from ckanext.datastore.backend import (
    DatastorePostgresqlBackend,
    DatastoreException
)

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

    def configure_datastore(self, config):
        self.backend.configure_datastore(config)

    # IConfigurer

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates')
        self.backend = DatastorePostgresqlBackend()

    # IConfigurable

    def configure(self, config):
        self.config = config

        # Legacy mode means that we have no read url. Consequently sql search
        # is not available and permissions do not have to be changed. In
        # legacy mode, the datastore runs on PG prior to 9.0 (for
        # example 8.4).
        self.legacy_mode = self.backend.is_legacy_mode(self.config)

        self.configure_datastore(config)
        # self.backend.configure_datastore(config)

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
        }
        if not self.legacy_mode:
            if self.backend.advanced_search_enabled():
                # Only enable search_sql if the config does not disable it
                actions.update({
                    'datastore_search_sql': action.datastore_search_sql,
                    'datastore_advanced_search': action.datastore_search_sql
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
            'datastore_change_permissions': auth.datastore_change_permissions
        }

    # IRoutes

    def before_map(self, m):
        m.connect(
            '/datastore/dump/{resource_id}',
            controller='ckanext.datastore.controller:DatastoreController',
            action='dump')
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

    # IDatastore

    def datastore_validate(self, *pargs, **kwargs):
        return self.backend.datastore_validate(*pargs, **kwargs)

    def datastore_delete(self, *pargs, **kwargs):
        return self.backend.datastore_delete(*pargs, **kwargs)

    def datastore_search(self, *pargs, **kwargs):
        return self.backend.datastore_search(*pargs, **kwargs)
