# encoding: utf-8

"""
Provides bridges between the model and plugin PluginImplementationss
"""
import logging
from operator import methodcaller

from sqlalchemy.orm.session import SessionExtension

import ckan.plugins as plugins


log = logging.getLogger(__name__)


class PluginSessionExtension(SessionExtension):
    """
    Class that calls plugins implementing ISession on SQLAlchemy
    SessionExtension events
    """

    def notify_observers(self, func):
        """
        Call func(observer) for all registered observers.

        :param func: Any callable, which will be called for each observer
        :returns: EXT_CONTINUE if no errors encountered, otherwise EXT_STOP
        """
        for observer in plugins.PluginImplementations(plugins.ISession):
            func(observer)

    def after_begin(self, session, transaction, connection):
        return self.notify_observers(
            methodcaller('after_begin', session, transaction, connection)
        )

    def before_flush(self, session, flush_context, instances):
        return self.notify_observers(
            methodcaller('before_flush', session, flush_context, instances)
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
