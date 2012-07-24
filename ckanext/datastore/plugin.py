import ckan.plugins as p
import ckanext.datastore.logic.action.create as action_create
import ckanext.datastore.logic.auth.create as auth_create


class DatastorePlugin(p.SingletonPlugin):
    '''
    Datastore plugin.
    '''
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)

    def get_actions(self):
        return {'datastore_create': action_create.datastore_create}

    def get_auth_functions(self):
        return {'datastore_create': auth_create.datastore_create}
