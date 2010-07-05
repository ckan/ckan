from sqlalchemy.orm import object_session
from sqlalchemy.orm.interfaces import MapperExtension, EXT_CONTINUE
from sqlalchemy.orm.session import SessionExtension
import blinker

import vdm.sqlalchemy

from ckan.lib.util import Enum

State = vdm.sqlalchemy.State

__all__ = ['Notification', 'PackageNotification', 'DatabaseNotification',
           'DomainObjectNotification', 'StopNotification',
           'ROUTING_KEYS', 'NotifierMapperTrigger',
           'PackageRelationNotifierMapperTrigger']

NOTIFYING_DOMAIN_OBJ_NAMES = ['Package', 'PackageResource']
DOMAIN_OBJECT_OPERATIONS = ('new', 'changed', 'deleted')
DomainObjectNotificationOperation = Enum('new', 'changed', 'deleted')
ROUTING_KEYS = ['db', 'stop'] + NOTIFYING_DOMAIN_OBJ_NAMES

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
        routing_key = notification_dict.pop('routing_key')
        assert routing_key in ROUTING_KEYS, routing_key
        # Work out what class of Notification it is
        if routing_key in NOTIFYING_DOMAIN_OBJ_NAMES:
            if routing_key == 'Package':
                cls = PackageNotification
            elif routing_key == 'PackageResource':
                cls = PackageResourceNotification
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
        '''Creates a suitable notification object, based on the type of the
        domain_object.'''
        assert domain_object.__class__.__name__ in NOTIFYING_DOMAIN_OBJ_NAMES, domain_object.__class__.__name__
        if cls == DomainObjectNotification:
            for subclass in [PackageNotification, PackageResourceNotification]:
                if domain_object.__class__.__name__ == subclass.domain_object_class:
                    cls = subclass
                    break
            assert cls != DomainObjectNotification, 'Could not create ' + \
                   'notification for domain object type: ' + \
                   domain_object.__class__.__name__
        assert domain_object.__class__.__name__ == cls.domain_object_class
        assert operation in DomainObjectNotificationOperation, operation
        object_type = domain_object.__class__.__name__
        return super(DomainObjectNotification, cls).create(\
            object_type,
            operation=operation,
            payload=domain_object.as_dict())

    @property
    def domain_object(self):
        return self['payload']

    def __repr__(self):
        return '<%s %s %s>' % (self.__class__.__name__, self['operation'], self['payload']['name'])

class PackageNotification(DomainObjectNotification):
    domain_object_class = 'Package'

    @property
    def package(self):
        return self['payload']

class PackageResourceNotification(DomainObjectNotification):
    domain_object_class = 'PackageResource'

    @property
    def resource(self):
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
        return self.notify(instance, instance, DomainObjectNotificationOperation.new)

    def after_update(self, mapper, connection, instance):
        return self.notify(instance, instance, DomainObjectNotificationOperation.changed)
            
    def notify(self, triggered_instance, notify_instance, operation):
        if self.check_real_change(triggered_instance):
            if notify_instance.state == State.DELETED:
                if notify_instance.all_revisions[1].state != State.DELETED:
                    # i.e. just deleted
                    self.queued_notifications.append(DomainObjectNotification.create(notify_instance, 'deleted'))
                # no notification sent if changed whilst deleted
            else:
                self.queued_notifications.append(DomainObjectNotification.create(notify_instance, operation))
                # can't send notification yet because the domain object may still
                # be in this thread's session so not yet flushed to the db table,
                # and another thread may want to access it. Therefore queue it
                # up until the commit is done.
        return EXT_CONTINUE

class PackageRelationNotifierMapperTrigger(NotifierMapperTrigger):
    def after_insert(self, mapper, connection, instance):
        return super(PackageRelationNotifierMapperTrigger, self).notify(instance, instance.package, DomainObjectNotificationOperation.changed)

    def after_update(self, mapper, connection, instance):
        print "TRIGGER", instance
        return super(PackageRelationNotifierMapperTrigger, self).notify(instance, instance.package, DomainObjectNotificationOperation.changed)

        


class NotifierSessionTrigger(SessionExtension):
    def after_commit(self, session):
        for notification in NotifierMapperTrigger.queued_notifications:
            notification.send_synchronously()
        NotifierMapperTrigger.queued_notifications = []

