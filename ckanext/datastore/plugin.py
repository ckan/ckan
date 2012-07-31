import ckan.plugins as p
import ckanext.datastore.logic.action.create as action_create
import ckanext.datastore.logic.action.delete as action_delete
import ckanext.datastore.logic.action.get as action_get
import ckanext.datastore.logic.auth.create as auth_create
import ckanext.datastore.logic.auth.delete as auth_delete
import ckanext.datastore.logic.auth.get as auth_get


class DatastoreException(Exception):
    pass


class DatastorePlugin(p.SingletonPlugin):
    '''
    Datastore plugin.
    '''
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)

    def configure(self, config):
        # check for ckan.datastore_write_url
        if (not 'ckan.datastore_write_url' in config):
            error_msg = 'ckan.datastore_write_url not found in config'
            raise DatastoreException(error_msg)

    def get_actions(self):
        return {'datastore_create': action_create.datastore_create,
                'datastore_delete': action_delete.datastore_delete,
                'datastore_search': action_get.datastore_search}

    def get_auth_functions(self):
        return {'datastore_create': auth_create.datastore_create,
                'datastore_delete': auth_delete.datastore_delete,
                'datastore_search': auth_get.datastore_search}
