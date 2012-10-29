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
        
        
    def get_updates_count(self):
        count = 0
        item_list = self.get_item_list()
        for item in item_list:
            if item.status in ['changed', 'added']:
                count += 1
        
        return count


    def update_item_list(self, data_by_definition, key_name):
        self.last_evaluated = datetime.datetime.now()

        if self.definition['data_type'] in ['dataset', 'user']:
            self._prepare_items()
            self._prepare_data_by_definition(data_by_definition, key_name)

            self._determine_added_items()
            self._determine_removed_items()
            self._determine_changed_items()
            self._determine_remaining_items()
        
        elif self.definition['data_type'] == 'data':
            pass
        
        self._save_items()
        
    def mark_item_list_changes_as_seen(self):
        self._item_list = self.get_item_list()
        self._delete_removed_items()
        self._set_status_to_seen()
        self._save_items()
        

    def _prepare_items(self):
        self._item_list = self.get_item_list()
        self._item_dict = dict([(item.key, item) for item in self._item_list])
        self._item_ids = set(self._item_dict.keys())


    def _prepare_data_by_definition(self, data_by_definition, key_name):
        if isinstance(data_by_definition, dict):
            self._item_data_dict_by_definition = data_by_definition
            
        elif isinstance(data_by_definition, list):
            self._item_data_dict_by_definition = {}
            
            for item_data in data_by_definition:
               self._item_data_dict_by_definition[self._get_key(item_data, key_name)] = item_data

        self._item_ids_by_definition = set(self._item_data_dict_by_definition.keys())
        
        
    def _get_key(self, item_data, key_name):
        if key_name:
            return item_data[key_name]
        
        return unicode(_hash(item_data))

  
    def _determine_added_items(self):
        self._added_item_ids = self._item_ids_by_definition - self._item_ids
        for item_id in self._added_item_ids:
            self._item_list.append(
                SubscriptionItem(subscription_id=self.id,
                                 data=self._item_data_dict_by_definition[item_id],
                                 key=item_id,
                                 status='added'))


    def _determine_removed_items(self):
        self._removed_item_ids = self._item_ids - self._item_ids_by_definition
        for item_id in self._removed_item_ids:
            self._item_dict[item_id].status='removed'


    def _determine_changed_items(self):
        self._remaining_item_ids = self._item_ids & self._item_ids_by_definition
        
        for item_id in self._remaining_item_ids:
            item_data = self._item_dict[item_id].data
            item_data_by_definition = self._item_data_dict_by_definition[item_id]
            if not self._item_data_equal_item_data(item_data, item_data_by_definition):
                self._item_dict[item_id].data = item_data_by_definition
                self._item_dict[item_id].status='changed'


    def _item_data_equal_item_data(self, item_data, equal_item_data):
        if set(item_data) ^ set(equal_item_data):
            return False
            
        for key, value in item_data.iteritems():
            if value != equal_item_data[key]:
                return False
            
        return True
    
    
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
    def __init__(self, subscription_id, data, key, status):
        self.id = _types.make_uuid()
        self.subscription_id = subscription_id
        if data is None:
            self.data = {}
        else:
            self.data = data
        self.key = key
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
    Column('key', types.UnicodeText, nullable=False),
    Column('data', _types.JsonDictType),
    Column('status', types.Boolean, nullable=False),
    )

meta.mapper(Subscription, subscription_table)
meta.mapper(SubscriptionItem, subscription_item_table)


def _hash(object_):
    if isinstance(object_, list) or isinstance(object_, set):
        return hash(tuple( [_hash(element) for element in object_] ))

    elif isinstance(object_, dict):
        return hash(tuple( [(hash(key), _hash(value)) for (key, value) in object_.items()] ))

    return hash(object_)

