"""
Provides bridges between the model and plugin ExtensionPoints
"""
import logging

from sqlalchemy.orm.interfaces import MapperExtension, EXT_CONTINUE, EXT_STOP
from sqlalchemy.orm.session import SessionExtension

from ckan.plugins import ExtensionPoint
from ckan.plugins import IMapperExtension, ISessionExtension

try:
    from operator import methodcaller
except ImportError:
    def methodcaller(name, *args, **kwargs):
        def caller(obj):
            return getattr(obj, name)(*args, **kwargs)
        return caller

log = logging.getLogger(__name__)

class ObserverNotifier(object):
    
    def notify_observers(self, func):
        try:
            for observer in self.observers:
                func(observer)
            return EXT_CONTINUE
        except Exception, e:
            log.exception(e)
            return EXT_STOP

class PluginMapperExtension(MapperExtension, ObserverNotifier):
    observers = ExtensionPoint(IMapperExtension)
    
    def before_insert(self, mapper, connection, instance):
        return self.notify_observers(
            methodcaller('before_insert', mapper, connection, instance)
        )

    def before_update(self, mapper, connection, instance):
        return self.notify_observers(
            methodcaller('before_update', mapper, connection, instance)
        )

    def before_delete(self, mapper, connection, instance):
        return self.notify_observers(
            methodcaller('before_delete', mapper, connection, instance)
        )

    def after_insert(self, mapper, connection, instance):
        return self.notify_observers(
            methodcaller('after_insert', mapper, connection, instance)
        )
                                     
    def after_update(self, mapper, connection, instance):
        return self.notify_observers(
            methodcaller('after_update', mapper, connection, instance)
        )
    
    def after_delete(self, mapper, connection, instance):
        return self.notify_observers(
            methodcaller('after_delete', mapper, connection, instance)
        )
        

class PluginSessionExtension(SessionExtension, ObserverNotifier):
    observers = ExtensionPoint(ISessionExtension)
    
    def after_begin(self, session, transaction, connection):
        return self.notify_observers(
            methodcaller('after_begin', session, transaction, connection)
        )
    
    def before_flush(self, session, flush_context, instances):
        return self.notify_observers(
            methodcaller('after_begin', session, flush_context, instances)
        )
                                  
    def after_flush(self, session, flush_context):
        return self.notify_observers(
            methodcaller('after_flush', session, flush_context)
        )
                                  
    def before_commit(self, session):
        return self.notify_observers(
            methodcaller('before_commit', session)
        )
    
    def after_commit(self, session):
        return self.notify_observers(
            methodcaller('after_commit', session)
        )
        
    def after_rollback(self, session):
        return self.notify_observers(
            methodcaller('after_rollback', session)
        )
