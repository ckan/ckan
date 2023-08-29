# encoding: utf-8

import logging
from typing import Any

from ckan.lib.search import SearchIndexError

import ckan.plugins as plugins
import ckan.model as model

log = logging.getLogger(__name__)

__all__ = ['DomainObjectModificationExtension']


class DomainObjectModificationExtension(plugins.SingletonPlugin):
    """
    Notify observers about domain object modifications before commit.

    Observers are other plugins implementing the IDomainObjectModification
    interface.
    """

    def before_commit(self, session: Any):
        self.notify_observers(session, self.notify)

    def notify_observers(self, session: Any, method: Any):
        session.flush()
        if not hasattr(session, '_object_cache'):
            return

        obj_cache = session._object_cache
        new = obj_cache['new']
        changed = obj_cache['changed']
        deleted = obj_cache['deleted']

        for obj in set(new):
            if isinstance(obj, (model.Package, model.Resource)):
                method(obj, model.DomainObjectOperation.new)
        for obj in set(deleted):
            if isinstance(obj, (model.Package, model.Resource)):
                method(obj, model.DomainObjectOperation.deleted)
        for obj in set(changed):
            if isinstance(obj, model.Resource):
                method(obj, model.DomainObjectOperation.changed)
            if getattr(obj, 'url_changed', False):
                for item in plugins.PluginImplementations(plugins.IResourceUrlChange):
                    item.notify(obj)


        changed_pkgs = set()
        new_pkg_ids = [obj.id for obj in new if isinstance(obj, model.Package)]
        for obj in changed:
            if isinstance(obj, model.Package) and obj.id not in new_pkg_ids:
                changed_pkgs.add(obj)

        for obj in new | changed | deleted:
            if not isinstance(obj, model.Package):
                try:
                    changed_pkgs.update(obj.related_packages())
                except AttributeError:
                    continue

        for obj in changed_pkgs:
            method(obj, model.DomainObjectOperation.changed)

    def notify(self, entity: Any, operation: Any):
        for observer in plugins.PluginImplementations(
                plugins.IDomainObjectModification):
            try:
                observer.notify(entity, operation)
            except SearchIndexError as search_error:
                log.exception(search_error)
                # Reraise, since it's pretty crucial to ckan if it can't index
                # a dataset
                raise
            except Exception as ex:
                log.exception(ex)
                # Don't reraise other exceptions since they are generally of
                # secondary importance so shouldn't disrupt the commit.
