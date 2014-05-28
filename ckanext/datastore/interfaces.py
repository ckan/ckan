import ckan.plugins.interfaces as interfaces


class IDataStore(interfaces.Interface):
    '''Allow changing DataStore queries'''

    def search_data(self, context, data_dict, query_dict, all_field_ids):
        return query_dict

    def where(self, filters, data_dict, all_field_ids):
        # TODO: Write docs
        '''
        :param filters: dictionary with non-processed filters
        :type filters: dictionary

        :returns: the filters dictionary with the elements that were processed
                  by this method removed, and the relative clauses list created
                  from them.
        '''
        clauses = []
        return clauses

    def validate_query(self, context, data_dict, all_field_ids):
        return data_dict
