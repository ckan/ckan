import ckan.plugins.interfaces as interfaces


class IDatastore(interfaces.Interface):
    '''Allow changing Datastore queries'''

    def datastore_validate_query(self, context, data_dict, all_field_ids):
        return data_dict

    def datastore_search(self, context, data_dict, all_field_ids, query_dict):
        return query_dict

    def datastore_delete(self, context, data_dict, all_field_ids, query_dict):
        return query_dict
