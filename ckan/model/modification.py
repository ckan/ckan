import logging

from vdm.sqlalchemy import State

from sqlalchemy.orm import object_session
from sqlalchemy.orm.interfaces import EXT_CONTINUE

from ckan.plugins import SingletonPlugin, PluginImplementations, implements
from ckan.plugins import ISession, IDomainObjectModification, IResourceUrlChange

from ckan.model.extension import ObserverNotifier
from ckan.model.domain_object import DomainObjectOperation

from ckan.model.package import Package
from ckan.model.resource import ResourceGroup, Resource
from ckan.model.package_extra import PackageExtra
from ckan.model.tag import PackageTag

log = logging.getLogger(__name__)

class DomainObjectModificationExtension(SingletonPlugin, ObserverNotifier):
    """
    A domain object level interface to change notifications

    Triggered by all edits to table and related tables, which we filter
    out with check_real_change.
    """

    implements(ISession, inherit=True)
    observers = PluginImplementations(IDomainObjectModification)

    def before_commit(self, session):

        session.flush()
        if not hasattr(session, '_object_cache'):
            return

        obj_cache = session._object_cache
        new = obj_cache['new']
        changed = obj_cache['changed']
        deleted = obj_cache['deleted']

        for obj in set(new):
            if isinstance(obj, (Package, Resource)):
                self.notify(obj, DomainObjectOperation.new)
        for obj in set(deleted):
            if isinstance(obj, (Package, Resource)):
                self.notify(obj, DomainObjectOperation.deleted)
        for obj in set(changed):
            if isinstance(obj, Resource):
                self.notify(obj, DomainObjectOperation.changed)
            if getattr(obj, 'url_changed', False):
                for item in PluginImplementations(IResourceUrlChange):
                    item.notify(obj)

        changed_pkgs = set(obj for obj in changed if isinstance(obj, Package))

        for obj in new | changed | deleted:
            if not isinstance(obj, Package):
                try:
                    related_packages = obj.related_packages()
                except AttributeError:
                    continue
                # this is needed to sort out vdm bug where pkg.as_dict does not
                # work when the package is deleted.
                for package in related_packages:
                    if package and package not in deleted | new:
                        changed_pkgs.add(package)
        for obj in changed_pkgs:
            self.notify(obj, DomainObjectOperation.changed)


    def notify(self, entity, operation):
        for observer in self.observers:
            try:
                observer.notify(entity, operation)
            except Exception, ex:
                log.exception(ex)
                # We reraise all exceptions so they are obvious there
                # is something wrong
                raise
