# encoding: utf-8

import logging
from typing import Optional

log = logging.getLogger(__name__)


class State(object):
    ACTIVE = u'active'
    DELETED = u'deleted'
    PENDING = u'pending'


class StatefulObjectMixin(object):
    __stateful__ = True
    state: Optional[str] = None

    def delete(self) -> None:
        log.debug('Running delete on %s', self)
        self.state = State.DELETED

    def undelete(self) -> None:
        self.state = State.ACTIVE

    def is_active(self) -> bool:
        # also support None in case this object is not yet refreshed ...
        return self.state is None or self.state == State.ACTIVE
