from sqlalchemy.orm import object_session
from sqlalchemy.orm.interfaces import MapperExtension, EXT_CONTINUE
from sqlalchemy.orm.session import SessionExtension
import blinker

import vdm.sqlalchemy

State = vdm.sqlalchemy.State

__all__ = ['Notification', 'PackageNotification', 'DatabaseNotification',
           'DomainObjectNotification', 'StopNotification',
           'ROUTING_KEYS']

NOTIFYING_DOMAIN_OBJ_NAMES = ['Package', 'PackageResource']
DOMAIN_OBJECT_OPERATIONS = ('new', 'changed', 'deleted')
ROUTING_KEYS = ['db', 'stop'] + NOTIFYING_DOMAIN_OBJ_NAMES

class Notification(dict):
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
        routing_key = notification_dict.pop('routing_key')
        assert routing_key in ROUTING_KEYS, routing_key
        # Work out what class of Notification it is
        if routing_key in NOTIFYING_DOMAIN_OBJ_NAMES:
            if routing_key == 'Package':
                cls = PackageNotification
            else:
                raise NotImplementedError()
        elif routing_key == 'db':
            cls = DatabaseNotification
        elif routing_key == StopNotification.msg:
            cls = StopNotification
        else:
            raise NotImplementedError()
        return cls(routing_key, **notification_dict)
        
    def send_synchronously(self):
        signal = blinker.signal(self['routing_key'])
        signal.send(self, **self)

class DomainObjectNotification(Notification):
    @classmethod
    def create(cls, domain_object, operation):
        assert domain_object.__class__.__name__ in NOTIFYING_DOMAIN_OBJ_NAMES
        assert domain_object.__class__.__name__ == cls.domain_object_class
        assert operation in DOMAIN_OBJECT_OPERATIONS
        object_type = domain_object.__class__.__name__
        return super(DomainObjectNotification, cls).create(\
            object_type,
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
        if instance.__class__.__name__ in NOTIFYING_DOMAIN_OBJ_NAMES and\
               self.check_real_change(instance):
            notification = PackageNotification.create(instance, 'new')
            self.queued_notifications.append(notification)
            # can't send this now because the domain object may still be
            # in this thread's session so not yet flushed to the db table,
            # and another thread may want to access it. Therefore queue it
            # up until the commit is done.
        return EXT_CONTINUE

    def after_update(self, mapper, connection, instance):
        if instance.__class__.__name__ in NOTIFYING_DOMAIN_OBJ_NAMES and\
               self.check_real_change(instance):
            if instance.state == State.DELETED:
                if instance.all_revisions[1].state != State.DELETED:
                    # i.e. just deleted
                    self.queued_notifications.append(PackageNotification.create(instance, 'deleted'))
                # no notification sent if changed whilst deleted
            else:
                self.queued_notifications.append(PackageNotification.create(instance, 'changed'))
        return EXT_CONTINUE

class NotifierSessionTrigger(SessionExtension):
    def after_commit(self, session):
        for notification in NotifierMapperTrigger.queued_notifications:
            notification.send_synchronously()
        NotifierMapperTrigger.queued_notifications = []

