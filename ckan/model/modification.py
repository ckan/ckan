import logging

import ckan.plugins as plugins
import extension
import domain_object
import package as _package
import resource

log = logging.getLogger(__name__)

__all__ = ['DomainObjectModificationExtension']

class DomainObjectModificationExtension(plugins.SingletonPlugin, extension.ObserverNotifier):
    """
    A domain object level interface to change notifications

    Triggered by all edits to table and related tables, which we filter
    out with check_real_change.
    """

    plugins.implements(plugins.ISession, inherit=True)
    observers = plugins.PluginImplementations(plugins.IDomainObjectModification)

    def before_commit(self, session):

        session.flush()
        if not hasattr(session, '_object_cache'):
            return

        obj_cache = session._object_cache
        new = obj_cache['new']
        changed = obj_cache['changed']
        deleted = obj_cache['deleted']

        for obj in set(new):
            if isinstance(obj, (_package.Package, resource.Resource)):
                self.notify(obj, domain_object.DomainObjectOperation.new)
        for obj in set(deleted):
            if isinstance(obj, (_package.Package, resource.Resource)):
                self.notify(obj, domain_object.DomainObjectOperation.deleted)
        for obj in set(changed):
            if isinstance(obj, resource.Resource):
                self.notify(obj, domain_object.DomainObjectOperation.changed)
            if getattr(obj, 'url_changed', False):
                for item in plugins.PluginImplementations(plugins.IResourceUrlChange):
                    item.notify(obj)

        changed_pkgs = set(obj for obj in changed if isinstance(obj, _package.Package))

        for obj in new | changed | deleted:
            if not isinstance(obj, _package.Package):
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
            self.notify(obj, domain_object.DomainObjectOperation.changed)


    def notify(self, entity, operation):
        for observer in self.observers:
            try:
                observer.notify(entity, operation)
            except Exception, ex:
                log.exception(ex)
                # We reraise all exceptions so they are obvious there
                # is something wrong
                raise
