# -*- coding: utf-8 -*-

import ckan.plugins as p
from ckan.types import SignalMapping


def x2(sender: int):
    return sender * 2


def x10(sender: int):
    return sender * 10


class ExampleISignalPlugin(p.SingletonPlugin):
    p.implements(p.ISignal)

    # ISignal

    def get_signal_subscriptions(self) -> SignalMapping:
        return {
            p.toolkit.signals.ckanext.signal(u'isignal_number'): [
                x2,
                {u'receiver': x10, u'sender': 10}
            ]
        }
