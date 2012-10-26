import ckan
import ckanext.lodstatsext.model.prefix as prefix
import ckanext.lodstatsext.model.store as store
import datetime
import dateutil.parser
import domain_object
import meta
from sqlalchemy import orm, types, Column, Table, ForeignKey
import types as _types

__all__ = ['Subscription', 'SubscriptionItem']



class Subscription(domain_object.DomainObject):
    def __init__(self, name = None, definition = None, owner_id = None):
        self.id = _types.make_uuid()
        self.definition = definition
        self.name = name
        self.owner_id = owner_id
        self.last_evaluated = datetime.datetime.now()
        self.last_modified = datetime.datetime.now()
        
        
    def get_item_list(self):
        query = meta.Session.query(SubscriptionItem)
        query = query.filter(SubscriptionItem.subscription_id == self.id)
        return query.all()


    def update_item_list(self, context, search_action):
        self.last_evaluated = datetime.datetime.now()

        if self.definition['data_type'] in ['dataset', 'user']:
            self._retrieve_items()
            self._retrieve_item_data_by_definition(context, search_action)
            
            self._determine_added_items()
            self._determine_removed_items()
            self._determine_remaining_items()
        
        elif self.definition['data_type'] == 'data':
            pass
        
        self._save_items()
        
    def mark_item_list_changes_as_seen(self):
        self._item_list = self.get_item_list()
        self._delete_removed_items()
        self._set_status_to_seen()
        self._save_items()
        

    def _retrieve_items(self):
        self._item_list = self.get_item_list()
        self._item_dict = dict([(item.data['id'], item) for item in self._item_list])
        self._item_ids = set(self._item_dict.keys())


    def _retrieve_item_data_by_definition(self, context, search_action):
        if self.definition['type'] == 'search':
            data_dict = {
                'q': self.definition['query'],
                'fq': '',
                'facet.field': ['groups', 'tags', 'res_format', 'license'],
                'start': 0,
                'rows': 20,
                'sort': None,
                'extras': {}
            }
            search_results = search_action(context, data_dict)

            self._item_data_list_by_definition = search_results['results']
        elif self.definition['type'] == 'semantic':
            prefix_query_string = 'prefix void: <http://rdfs.org/ns/void#>\nprefix xs: <http://www.w3.org/2001/XMLSchema#>'
            select_query_string = 'select ?dataset'
            where_query_string = 'where\n{\n    ?dataset a void:Dataset.\n'
            group_by_query_string = ''

            if 'topics' in self.definition['filters']:
                for topic in self.definition['filters']['topics']:
                #TODO: differentiate between vocabularies, classes, properties and injections
                    where_query_string += '?dataset void:vocabulary <' + topic + '>.\n'
                    
            if 'location' in self.definition['filters']:
                location = self.definition['filters']['location']
                where_query_string += '?dataset void:propertyPartition ?latPropertyPartition.\n'
                where_query_string += '?latPropertyPartition void:property <http://www.w3.org/2003/01/geo/wgs84_pos#lat>.\n'
                where_query_string += '?latPropertyPartition void:minValue ?minLatitude.\n'
                where_query_string += '?latPropertyPartition void:maxValue ?maxLatitude.\n'
                
                where_query_string += '?dataset void:propertyPartition ?longPropertyPartition.\n'
                where_query_string += '?longPropertyPartition void:property <http://www.w3.org/2003/01/geo/wgs84_pos#long>.\n'
                where_query_string += '?longPropertyPartition void:minValue ?minLongitude.\n'
                where_query_string += '?longPropertyPartition void:maxValue ?maxLongitude.\n'

                where_query_string += 'filter(' + location['radius'] + ' + fn:max(bif:pi()*6378*(?maxLatitude - ?minLatitude)/180, 2*bif:pi()*6378*bif:cos((?maxLatitude - ?minLatitude)/2)*(?maxLongitude - ?minLongitude)/360)/2 > (2 * 3956 * bif:asin(bif:sqrt((bif:power(bif:sin(2*bif:pi() + (' + location['latitude'] + ' - (?minLatitude + ?maxLatitude)/2)*bif:pi()/360), 2) + bif:cos(2*bif:pi() + ' + location['latitude'] + '*bif:pi()/180) * bif:cos(2*bif:pi() + (?minLatitude + ?maxLatitude)/2*bif:pi()/180) * bif:power(bif:sin(2*bif:pi() + (' + location['longitude'] + ' - (?minLongitude + ?maxLongitude)/2)*bif:pi()/360), 2))))))\n'

            if 'time' in self.definition['filters']:
                time = self.definition['filters']['time']
                where_query_string += '''
                                      ?dataset void:propertyPartition ?dateTimePropertyPartition.
                                      ?dateTimePropertyPartition void:minValue ?minDateTime.
                                      ?dateTimePropertyPartition void:maxValue ?maxDateTime.
                                      filter(datatype(?minDateTime) = xs:dateTime)
                                      filter(datatype(?maxDateTime) = xs:dateTime)
                                      '''
                #virtuoso bugs make this kind of queries impossible
                #if self.definition['time']['type'] == 'span':
                #    where_query_string += 'filter('
                #    where_query_string += 'if(?minDateTime > "' + self.definition['time']['min'] + '"^^xs:dateTime, ?minDateTime, "' + self.definition['time']['min'] + '"^^xs:dateTime) <='
                #    where_query_string += 'if(?maxDateTime < "' + self.definition['time']['max'] + '"^^xs:dateTime, ?maxDateTime, "' + self.definition['time']['max'] + '"^^xs:dateTime)'
                #    where_query_string += ')'

                #if self.definition['time']['type'] == 'point':
                #    where_query_string += 'filter('
                #    where_query_string += 'if(?minDateTime > bif:dateadd("day", ' + self.definition['time']['variance'] + ', "' + self.definition['time']['point'] + '"^^xs:dateTime), ?minDateTime, bif:dateadd("day", ' + self.definition['time']['variance'] + ', "' + self.definition['time']['point'] + '"^^xs:dateTime)) <='
                #    where_query_string += 'if(?maxDateTime < bif:dateadd("day", ' + self.definition['time']['variance'] + ', "' + self.definition['time']['point'] + '"^^xs:dateTime), ?maxDateTime, bif:dateadd("day", ' + self.definition['time']['variance'] + ', "' + self.definition['time']['point'] + '"^^xs:dateTime))'
                #    where_query_string += ')'
                #workaround
                select_query_string += ' (min(?minDateTime) as ?minDateTime) (max(?maxDateTime) as ?maxDateTime)'
                group_by_query_string = 'group by ?dataset'

            where_query_string += '}'
     
            query_string = prefix_query_string + '\n' + \
                           select_query_string + '\n' + \
                           where_query_string + '\n' + \
                           group_by_query_string + '\n'
                           
                           
            rows = store.root.query(query_string)
            
            #FIXME: workaround as long as virtuoso is not functioning properly
            if 'time' in self.definition['filters']:
                time = self.definition['filters']['time']
                [row for row in rows if row['minDateTime']['value'] != '']
                if time['type'] == 'span':
                    [row for row in rows if max(row['minDateTime']['value'], time['min']) <= min(row['maxDateTime']['value'], time['max'])]
                if time['type'] == 'point':
                    point = dateutil.parser.parse(time['point'])
                    variance = datetime.timedelta(days=int(time['variance']))
                    min_ = point - variance
                    max_ = point + variance

                    rows_copy = rows
                    rows = []                    
                    for row in rows_copy:
                        if max(row['minDateTime']['value'], min_.isoformat()) <= min(row['maxDateTime']['value'], max_.isoformat()):
                            rows.append(row)

                    
            datasets = [ckan.lib.helpers.uri_to_object(row['dataset']['value']) for row in rows]
            datasets = [ckan.lib.dictization.model_dictize.package_dictize(dataset, context) for dataset in datasets if dataset is not None]

            self._item_data_list_by_definition = datasets

        elif self.definition['type'] == 'sparql':
            #TODO: check for access rights
            rows = store.root.query(self.definition['query'])

            datasets = [ckan.lib.helpers.uri_to_object(row['dataset']['value']) for row in rows]
            datasets = [ckan.lib.dictization.model_dictize.package_dictize(dataset, context) for dataset in datasets if dataset is not None]

            self._item_data_list_by_definition = datasets
        
        if self.definition['type'] in ['search', 'semantic', 'sparql']:
            self._item_data_dict_by_definition = dict([(item_data['id'], item_data) for item_data in self._item_data_list_by_definition])
            self._item_ids_by_definition = set(self._item_data_dict_by_definition.keys())

  
    def _determine_added_items(self):
        self._added_item_ids = self._item_ids_by_definition - self._item_ids
        for item_id in self._added_item_ids:
            self._item_list.append(
                SubscriptionItem(subscription_id=self.id,
                                 data=self._item_data_dict_by_definition[item_id],
                                 status='added'))


    def _determine_removed_items(self):
        self._removed_item_ids = self._item_ids - self._item_ids_by_definition
        for item_id in self._removed_item_ids:
            self._item_dict[item_id].status='removed'


    def _determine_remaining_items(self):
        self._remaining_item_ids = self._item_ids & self._item_ids_by_definition
        
        
    def _delete_removed_items(self):
        self._item_list = [item for item in self._item_list if item.status != 'removed']
        query = meta.Session.query(SubscriptionItem)
        query = query.filter(SubscriptionItem.subscription_id == self.id)
        query = query.filter(SubscriptionItem.status == 'removed')
        query.delete()


    def _set_status_to_seen(self):
        for item in self._item_list:
            item.status = 'seen'
        
        
    def _save_items(self):
        meta.Session.add_all(self._item_list)


class SubscriptionItem(domain_object.DomainObject):
    def __init__(self, subscription_id=None, data=None, status='seen'):
        self.id = _types.make_uuid()
        self.subscription_id = subscription_id
        if data is None:
            self.data = {}
        else:
            self.data = data
        self.status = status


subscription_table = Table(
    'subscription', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('definition', _types.JsonDictType, nullable=False),
    Column('name', types.UnicodeText, nullable=False),
    Column('owner_id', types.UnicodeText, ForeignKey('user.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
    Column('last_evaluated', types.DateTime, nullable=False),
    Column('last_modified', types.DateTime, nullable=False),
    )

subscription_item_table = Table(
    'subscription_item', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('subscription_id', types.UnicodeText, ForeignKey('subscription.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
    Column('data', _types.JsonDictType),
    Column('status', types.Boolean, nullable=False),
    )

meta.mapper(Subscription, subscription_table)
meta.mapper(SubscriptionItem, subscription_item_table)
