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


    def update_item_list(self, data_list_by_definition):
        self.last_evaluated = datetime.datetime.now()

        if self.definition['data_type'] in ['dataset', 'user']:
            self._retrieve_items()
            self._prepare_data_list_by_definition(data_list_by_definition)

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
        

    def _retrieve_items(self):
        self._item_list = self.get_item_list()
        self._item_dict = dict([(item.data['id'], item) for item in self._item_list])
        self._item_ids = set(self._item_dict.keys())


    def _retrieve_item_data_by_definition(self, context, search_action):
        #TODO: check for access rights
        rows = store.user.query(self.definition['query'])

        datasets = [ckan.lib.helpers.uri_to_object(row['dataset']['value']) for row in rows]
        datasets = [ckan.lib.dictization.model_dictize.package_dictize(dataset, context) for dataset in datasets if dataset is not None]

        self._item_data_list_by_definition = datasets
    
    
    def _prepare_data_list_by_definition(self, data_list_by_definition):
        self._item_data_list_by_definition = data_list_by_definition
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
