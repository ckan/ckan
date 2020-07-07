# -*- coding: utf-8 -*-

import ckan.plugins as p


class ExampleHumanizerPlugin(p.SingletonPlugin, p.toolkit.DefaultGroupForm):
    p.implements(p.ITemplateHelpers)
    p.implements(p.IGroupForm)

    def get_helpers(self):
        return {
            u'humanize_entity_type': humanize_entity_type
        }

    def group_types(self):
        return (u'custom_group',)

    def is_fallback(self):
        return False


@p.toolkit.chained_helper
def humanize_entity_type(next_helper, entity_type, object_type, purpose):
    if purpose == u'add link':
        tpl = p.toolkit._(u"Create new {object_type}")
        type_label = object_type.replace(u"_", u" ").capitalize()
        return tpl.format(object_type=type_label)
    return next_helper(entity_type, object_type, purpose)
