# -*- coding: utf-8 -*-

import ckan.plugins as p


class ActionLogger(object):
    def __init__(self):
        self.actions = []

    def __call__(self, sender, **kwargs):
        self.actions.append(sender)

    def reset(self):
        self.actions[:] = []


action_logger = ActionLogger()


def x2(sender):
    return sender * 2


def x10(sender):
    return sender * 10


class ExampleISignalPlugin(p.SingletonPlugin):
    p.implements(p.ISignal)

    # ISignal

    def get_signal_subscriptions(self):
        return {
            p.toolkit.signals.before_action: [action_logger],
            p.toolkit.signals.ckanext.signal(u'isignal_number'): [
                x2,
                {'receiver': x10, 'sender': 10}
            ]
        }
