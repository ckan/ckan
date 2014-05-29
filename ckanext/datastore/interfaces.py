import ckan.plugins.interfaces as interfaces


class IDatastore(interfaces.Interface):
    '''Allow changing Datastore queries'''

    def search_data(self, context, data_dict, all_field_ids, query_dict):
        return query_dict

    def delete_data(self, context, data_dict, all_field_ids, query_dict):
        return query_dict

    def validate_query(self, context, data_dict, all_field_ids):
        return data_dict
