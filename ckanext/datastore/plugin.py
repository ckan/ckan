import ckan.plugins as p
import ckanext.datastore.logic.action as action
import ckanext.datastore.logic.auth as auth


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
        return {'datastore_create': action.datastore_create,
                'datastore_delete': action.datastore_delete,
                'datastore_search': action.datastore_search}

    def get_auth_functions(self):
        return {'datastore_create': auth.datastore_create,
                'datastore_delete': auth.datastore_delete,
                'datastore_search': auth.datastore_search}
