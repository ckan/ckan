# -*- coding: utf-8 -*-

import ckan.plugins as p
from ckan.lib.humanize import BaseHumanizer


class ExampleHumanizerPlugin(p.SingletonPlugin, p.toolkit.DefaultGroupForm):
    p.implements(p.IConfigurer)
    p.implements(p.IGroupForm)

    def update_config(self, config_):
        p.toolkit.add_humanizer(u'entity_type', CustomHumanizer)

    def group_types(self):
        return (u'custom_group',)

    def is_fallback(self):
        return False


class CustomHumanizer(BaseHumanizer):
    def add_link(self, term, entity_type):
        return u"Create new {}".format(term)
