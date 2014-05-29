import ckan.plugins.interfaces as interfaces


class IDataStore(interfaces.Interface):
    '''Allow changing DataStore queries'''

    def search_data(self, context, data_dict, query_dict, all_field_ids):
        return query_dict

    def delete_data(self, context, data_dict, query_dict, all_field_ids):
        return query_dict

    def validate_query(self, context, data_dict, all_field_ids):
        return data_dict
