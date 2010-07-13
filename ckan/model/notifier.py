from sqlalchemy.orm import object_session
from sqlalchemy.orm.interfaces import MapperExtension, EXT_CONTINUE
from sqlalchemy.orm.session import SessionExtension
import blinker

import vdm.sqlalchemy

from ckan.lib.util import Enum

State = vdm.sqlalchemy.State

__all__ = ['Notification', 'PackageNotification', 'ResourceNotification',
           'DatabaseNotification',
           'DomainObjectNotification', 'StopNotification',
           'ROUTING_KEYS', 'NotifierMapperTrigger',
           'NotificationError']

NOTIFYING_DOMAIN_OBJ_NAMES = ['Package', 'Resource']
ROUTING_KEYS = ['db', 'stop'] + NOTIFYING_DOMAIN_OBJ_NAMES

class Notifications(object):
    '''Stores info about all notification objects.'''
    # Using singleton to avoid any processing during import of this file
    class _Notifications(object):
        def __init__(self):
            self.type_info = [
                #(routing key, notification class)
                ('Package', PackageNotification),
                ('Resource', ResourceNotification),
                ('db', DatabaseNotification),
                ('stop', StopNotification),
                ]

            self.classes_by_routing_key = {}
            for routing_key, notification_class in self.type_info:
                self.classes_by_routing_key[routing_key] = notification_class

            self.routing_keys_by_class = {}
            for routing_key, notification_class in self.type_info:
                self.routing_keys_by_class[notification_class] = routing_key

            self.domain_object_notifications = {}
            self.domain_object_notifications_by_class = {}
            for routing_key, notification_class in self.type_info:
                if hasattr(notification_class, 'domain_object_class'):
                    classes = notification_class.domain_object_class.split()
                    self.domain_object_notifications[notification_class] = classes
                    for class_ in classes:
                        self.domain_object_notifications_by_class[class_] = notification_class
        
    @classmethod
    def instance(cls):
        if not hasattr(cls, '_instance'):
            cls._instance = cls._Notifications()
        return cls._instance

    def __getattr__(self, attr):
        return getattr(self.instance(), attr)
    
    
DomainObjectNotificationOperation = Enum('new', 'changed', 'deleted')
    

class NotificationError(Exception):
    pass

class Notification(dict):
    '''This is the message that is sent in both synchronous and asynchronous
    notifications. It has various subclasses depending on the payload.'''
    def __init__(self, routing_key, operation=None, payload=None):
        '''This should only be called by create or recreate methods.'''
        self['routing_key'] = routing_key
        self['operation'] = operation
        self['payload'] = payload

    @classmethod
    def create(cls, routing_key, **kwargs):
        '''Call to create a notification from scratch.'''
        return cls(routing_key, **kwargs)

    @staticmethod
    def recreate_from_dict(notification_dict):
        '''Call to recreate a notification from its queue representation.'''
        if not notification_dict.has_key('routing_key'):
            raise NotificationError('Missing a routing_key')
        routing_key = notification_dict.pop('routing_key')
        cls = Notifications.instance().classes_by_routing_key[routing_key]
        try:
            return cls(routing_key, **notification_dict)
        except TypeError:
            # python 2.6.2 get errors (not on 2.6.5 though!)
            # TypeError: __init__() keywords must be strings
            newdict = {}
            for k,v in notification_dict.items():
                newdict[str(k)] = v
            return cls(routing_key, **newdict)
        
    def send_synchronously(self):
        signal = blinker.signal(self['routing_key'])
        signal.send(self, **self)

class DomainObjectNotification(Notification):
    @classmethod
    def create(cls, domain_object, operation):
        '''Creates a suitable notification object, based on the type of the
        domain_object.'''
        # Change cls to the appropriate Notification subclass
        # e.g. if domain_object is Package then cls becomes PackageNotification
        cls = Notifications.instance().domain_object_notifications_by_class.get(domain_object.__class__.__name__, cls)
        routing_key = Notifications.instance().routing_keys_by_class[cls]
        assert operation in DomainObjectNotificationOperation, operation
        return super(DomainObjectNotification, cls).create(\
            routing_key,
            operation=operation,
            payload=domain_object.as_dict())

    @property
    def domain_object(self):
        return self['payload']


class PackageNotification(DomainObjectNotification):
    domain_object_class = 'Package'

    @property
    def package(self):
        return self['payload']

    def __repr__(self):
        return '<%s %s %s>' % (self.__class__.__name__, self['operation'], self['payload']['name'])

class ResourceNotification(DomainObjectNotification):
    domain_object_class = 'PackageResource'

    @property
    def resource(self):
        return self['payload']

    def __repr__(self):
        return '<%s %s %s>' % (self.__class__.__name__, self['operation'], self['payload']['id'])

class DatabaseNotification(Notification):
    @classmethod
    def create(cls, operation):
        assert operation in ('clean', 'rebuild')
        routing_key = 'db'
        return super(DatabaseNotification, cls).create(\
            routing_key, operation=operation)

class StopNotification(Notification):
    '''Used to stop the notification service down during tests.'''
    msg = 'stop'
    
    @classmethod
    def create(cls):
        return super(StopNotification, cls).create(cls.msg)


class NotifierMapperTrigger(MapperExtension):
    '''Triggered by all edits to table (and related tables, which we filter
    out with check_real_change).'''
    def check_real_change(self, instance):
        if not instance.revision:
            return False
        return object_session(instance).is_modified(instance, include_collections=False)

    queued_notifications = []
    
    def after_insert(self, mapper, connection, instance):
        return self.send_notifications(instance, DomainObjectNotificationOperation.new)

    def after_update(self, mapper, connection, instance):
        return self.send_notifications(instance, DomainObjectNotificationOperation.changed)
            
    def send_notifications(self, instance, operation):
        '''Called when an db object changes, this method works out what
        notifications need to be sent and calls send_notification to do it.
        '''
        from package import Package
        from resource import PackageResource
        from extras import PackageExtra
        from tag import PackageTag
        if self.check_real_change(instance):
            if isinstance(instance, Package):
                self.send_notification(instance, operation)
            elif isinstance(instance, PackageResource):
                self.send_notification(instance, operation)
                self.send_notification(instance.package, DomainObjectNotificationOperation.changed)
            elif isinstance(instance, (PackageExtra, PackageTag)):
                self.send_notification(instance.package, DomainObjectNotificationOperation.changed)
            else:
                raise NotImplementedError, instance
        return EXT_CONTINUE

    def send_notification(self, notify_instance, operation):
        if notify_instance.state == State.DELETED:
            if notify_instance.all_revisions and notify_instance.all_revisions[1].state != State.DELETED:
                # i.e. just deleted
                self.add_notification_to_queue(DomainObjectNotification.create(notify_instance, 'deleted'))
            # no notification sent if changed whilst deleted
        else:
            self.add_notification_to_queue(DomainObjectNotification.create(notify_instance, operation))

    def add_notification_to_queue(self, notification):
        '''We can\'t send notification yet because the domain object may still
        be in this thread\'s session so not yet flushed to the db table,
        and another thread may want to access it. Therefore queue it
        up until the commit is done.'''
        self.queued_notifications.append(notification)
        

class NotifierSessionTrigger(SessionExtension):
    def after_commit(self, session):
        for notification in NotifierMapperTrigger.queued_notifications:
            notification.send_synchronously()
        NotifierMapperTrigger.queued_notifications = []

