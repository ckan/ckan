import logging
import ckan.plugins as p
import ckanext.datastore_htsql.logic.action as action
import ckan.logic as logic

log = logging.getLogger(__name__)
_get_or_bust = logic.get_or_bust


class DatastoreHTSQLPlugin(p.SingletonPlugin):
    '''
    Extends the datastore to support htsql
    '''
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IActions)

    def configure(self, config):
        self.config = config

    def get_actions(self):
        return {'datastore_search_htsql': action.datastore_search_htsql}
