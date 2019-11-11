# encoding: utf-8

import datetime

from sqlalchemy import Column, DateTime, Text, Boolean

import domain_object
import meta


__all__ = ['System', 'State', 'StatefulObjectMixin']
log = __import__('logging').getLogger(__name__)


class System(domain_object.DomainObject):

    name = 'system'

    def __unicode__(self):
        return u'<%s>' % self.__class__.__name__

    def purge(self):
        pass

    @classmethod
    def by_name(cls, name):
        return System()


# VDM-specific domain objects
class State(object):
    ACTIVE = u'active'
    DELETED = u'deleted'
    PENDING = u'pending'


class StatefulObjectMixin(object):
    __stateful__ = True

    def delete(self):
        log.debug('Running delete on %s', self)
        self.state = State.DELETED

    def undelete(self):
        self.state = State.ACTIVE

    def is_active(self):
        # also support None in case this object is not yet refreshed ...
        return self.state is None or self.state == State.ACTIVE
