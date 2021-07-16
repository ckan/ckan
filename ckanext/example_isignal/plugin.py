# -*- coding: utf-8 -*-

import ckan.plugins as p


def x2(sender):
    return sender * 2


def x10(sender):
    return sender * 10


class ExampleISignalPlugin(p.SingletonPlugin):
    p.implements(p.ISignal)

    # ISignal

    def get_signal_subscriptions(self):
        return {
            p.toolkit.signals.ckanext.signal('isignal_number'): [
                x2,
                {'receiver': x10, 'sender': 10}
            ]
        }
