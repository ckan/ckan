from vdm.sqlalchemy import State

from sqlalchemy.orm import object_session
from sqlalchemy.orm.interfaces import EXT_CONTINUE

from ckan.plugins import SingletonPlugin, PluginImplementations, implements
from ckan.plugins import IMapper, IDomainObjectModification

from ckan.model.extension import ObserverNotifier
from ckan.model.domain_object import DomainObjectOperation

from ckan.model.package import Package
from ckan.model.resource import ResourceGroup, Resource
from ckan.model.package_extra import PackageExtra
from ckan.model.tag import PackageTag


class DomainObjectModificationExtension(SingletonPlugin, ObserverNotifier):
    """
    A domain object level interface to change notifications

    Triggered by all edits to table and related tables, which we filter
    out with check_real_change.
    """

    implements(IMapper, inherit=True)
    observers = PluginImplementations(IDomainObjectModification)
    
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
        
    def before_delete(self, mapper, connection, instance):
        return self.send_notifications(instance,
            DomainObjectOperation.deleted
        )

    def send_notifications(self, instance, operation):
        """
        Called when a db object changes, this method works out what
        notifications need to be sent and calls send_notification to do it.
        """
        if not (operation == DomainObjectOperation.deleted or self.check_real_change(instance)):
            return EXT_CONTINUE

        if isinstance(instance, Package):
            self.notify(instance, operation)
        elif isinstance(instance, ResourceGroup):
            self.notify(instance.package, DomainObjectOperation.changed)
        elif isinstance(instance, Resource):
            self.notify(instance.resource_group.package, DomainObjectOperation.changed)
        elif isinstance(instance, (PackageExtra, PackageTag)):
            self.notify(instance.package, DomainObjectOperation.changed)
        else:
            raise NotImplementedError(instance)

        return EXT_CONTINUE

    def notify(self, entity, operation):
        for observer in self.observers:
            observer.notify(entity, operation)
