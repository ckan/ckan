# encoding: utf-8

log = __import__('logging').getLogger(__name__)


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
