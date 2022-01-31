# encoding: utf-8

import logging

from sqlalchemy.orm.exc import UnmappedInstanceError

from ckan.lib.search import SearchIndexError
from ckan.common import g

import ckan.plugins as plugins
import ckan.model as model


log = logging.getLogger(__name__)

__all__ = ['DomainObjectModificationExtension']


class DomainObjectModificationExtension(plugins.SingletonPlugin):
    """
    A domain object level interface to change notifications

    """

    def before_commit(self, session):
        self.notify_observers(session, self.notify)

    def notify_observers(self, session, method):
        session.flush()
        if not hasattr(session, '_object_cache'):
            return

        obj_cache = session._object_cache
        new = obj_cache['new']
        changed = obj_cache['changed']
        deleted = obj_cache['deleted']

        for obj in set(new):
            if isinstance(obj, (model.package.Package, model.resource.Resource)):
                method(obj, model.domain_object.DomainObjectOperation.new)
        for obj in set(deleted):
            if isinstance(obj, (model.package.Package, model.resource.Resource)):
                method(obj, model.domain_object.DomainObjectOperation.deleted)
        for obj in set(changed):
            if isinstance(obj, model.resource.Resource):
                method(obj, model.domain_object.DomainObjectOperation.changed)
            if getattr(obj, 'url_changed', False):
                for item in plugins.PluginImplementations(plugins.IResourceUrlChange):
                    item.notify(obj)

        changed_pkgs = set(obj for obj in changed
                           if isinstance(obj, model.package.Package))

        for obj in new | changed | deleted:
            if not isinstance(obj, model.package.Package):
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
            method(obj, model.domain_object.DomainObjectOperation.changed)

    def notify(self, entity, operation):
        for observer in plugins.PluginImplementations(
                plugins.IDomainObjectModification):
            try:
                observer.notify(entity, operation)
            except SearchIndexError as search_error:
                log.exception(search_error)

                # userobj must be available inside rendered error template,
                # though it become unbounded after session rollback because
                # of this error. Expunge will prevent `UnboundedInstanceError`
                # raised from error template.
                try:
                    model.Session.expunge(g.userobj)
                # AttributeError - there is no such prop in `g`
                # UnmappedInstanceError - g.userobj is None or empty string.
                except (AttributeError, UnmappedInstanceError):
                    pass

                # Reraise, since it's pretty crucial to ckan if it can't index
                # a dataset
                raise
            except Exception as ex:
                log.exception(ex)
                # Don't reraise other exceptions since they are generally of
                # secondary importance so shouldn't disrupt the commit.
