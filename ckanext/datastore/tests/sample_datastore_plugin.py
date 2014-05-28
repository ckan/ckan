import ckan.plugins as p

import ckanext.datastore.interfaces as interfaces


class SampleDataStorePlugin(p.SingletonPlugin):
    p.implements(interfaces.IDataStore)

    def where(self, filters, all_field_ids):
        clauses = []
        if 'age_between' in filters:
            age_between = filters['age_between']

            clause = ('"age" >= %s AND "age" <= %s',
                      age_between[0], age_between[1])
            clauses.append(clause)
        if 'age_not_between' in filters:
            age_not_between = filters['age_not_between']

            clause = ('"age" < %s OR "age" > %s',
                      age_not_between[0], age_not_between[1])
            clauses.append(clause)
        return clauses

    def validate_query(self, context, data_dict, all_field_ids):
        valid_filters = ('age_between', 'age_not_between')
        filters = data_dict.get('filters', {})
        for key in filters.keys():
            if key in valid_filters:
                del filters[key]

        return data_dict
