import ckan.plugins.interfaces as interfaces


class IDataStore(interfaces.Interface):
    '''Allow changing DataStore queries'''

    def where(self, filters):
        '''
        :param filters: dictionary with non-processed filters
        :type filters: dictionary

        :returns: the filters dictionary with the elements that were processed
                  by this method removed, and the relative clauses list created
                  from them.
        '''
        clauses = []
        return filters, clauses
