from vdm.sqlalchemy import State

from sqlalchemy.orm import object_session
from sqlalchemy.orm.interfaces import EXT_CONTINUE

from ckan.plugins import SingletonPlugin, ExtensionPoint, implements
from ckan.plugins import IMapperExtension, IDomainObjectModification

from ckan.model.extension import ObserverNotifier
from ckan.model.domain_object import DomainObjectOperation

from ckan.model.package import Package
from ckan.model.resource import PackageResource
from ckan.model.package_extra import PackageExtra
from ckan.model.tag import PackageTag

try:
    from operator import methodcaller
except ImportError:
    def methodcaller(name, *args, **kwargs):
        "Replaces stdlib operator.methodcaller in python <2.6"
        def caller(obj):
            return getattr(obj, name)(*args, **kwargs)
        return caller


class DomainObjectModificationExtension(SingletonPlugin, ObserverNotifier):
    """
    A domain object level interface to change notifications

    Triggered by all edits to table and related tables, which we filter
    out with check_real_change.
    """

    implements(IMapperExtension, inherit=True)
    observers = ExtensionPoint(IDomainObjectModification)
    
    def check_real_change(self, instance):
        """
        Return True if the change concerns an object with revision information
        and has been modifed in the current SQLAlchemy session.
        """
        if not instance.revision:
            return False
        return object_session(instance).is_modified(
            instance, include_collections=False
        )

    def after_insert(self, mapper, connection, instance):
        return self.send_notifications(instance,
            DomainObjectOperation.new
        )

    def after_update(self, mapper, connection, instance):
        return self.send_notifications(instance,
            DomainObjectOperation.changed
        )

    def send_notifications(self, instance, operation):
        """
        Called when a db object changes, this method works out what
        notifications need to be sent and calls send_notification to do it.
        """
        if not self.check_real_change(instance):
            return EXT_CONTINUE

        if isinstance(instance, Package):
            self.notify(instance, operation)
        elif isinstance(instance, PackageResource):
            self.notify(instance, operation)
            self.notify(instance.package, DomainObjectOperation.changed)
        elif isinstance(instance, (PackageExtra, PackageTag)):
            self.notify(instance.package, DomainObjectOperation.changed)
        else:
            raise NotImplementedError(instance)

        return EXT_CONTINUE

    def notify(self, entity, operation):
        for observer in self.observers:
            observer.notify(entity, operation)
