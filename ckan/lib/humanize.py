# -*- coding: utf-8 -*-

import logging
from ckan.common import _

log = logging.getLogger(__name__)

def reset_translators():
    for k in _instances:
        _instances[k] = None

    # First base will always be provided by current module. We want to
    # keep it as fallback
    for k, v in _bases.items():
        _bases[k] = v[:1]


def get_translator(type_, **kwargs):
    if not _instances[type_]:
        _instances[type_] = type(
            type_,
            tuple(reversed(_bases[type_])),
            kwargs
        )()
    return _instances[type_]


class BaseTranslator(object):
    def _prepare_term(self, term):
        return term.replace(u'_', u' ').capitalize()

    def _default(self, term, **kwargs):
        return term

    def __call__(self, purpose, term, *args, **kwargs):
        handler = getattr(self, purpose.replace(u' ', u'_'), None)
        term = self._prepare_term(term)
        if handler:
            return handler(term, *args, **kwargs)
        log.warning(u'%s has no handlers for "%s"', self.__class__, purpose)
        return self._default(term, **kwargs)


class EntityTypeTranslator(BaseTranslator):
    def add_link(self, term, entity_type):
        return _('Add {object_name}').format(object_name=term)

    def breadcrumb(self, term, entity_type):
        return _('{object_name}s').format(object_name=term)

    def facet_label(self, term, entity_type):
        return _('{object_name}s').format(object_name=term)

    def page_title(self, term, entity_type):
        return _('{object_name}s').format(object_name=term)

    def create_title(self, term, entity_type):
        return _('Create {object_name}').format(object_name=term)

    def content_tab(self, term, entity_type):
        return _('{object_name}').format(object_name=term)

    def default_label(self, term, entity_type):
        return _('{object_name}').format(object_name=term)

    def no_label(self, term, entity_type):
        return _('No {object_name}').format(object_name=term)

    def form_label(self, term, entity_type):
        return _('{object_name} Form').format(object_name=term)

    def edit_label(self, term, entity_type):
        return _('Edit {object_name}').format(object_name=term)

    def update_label(self, term, entity_type):
        return _('Update {object_name}').format(object_name=term)

    def create_label(self, term, entity_type):
        return _('Create {object_name}').format(object_name=term)

    def save_label(self, term, entity_type):
        return _('Save {object_name}').format(object_name=term)

    def sidebar_label(self, term, entity_type):
        return _('{object_name}').format(object_name=term)

    def my_label(self, term, entity_type):
        return _('My {object_name}s').format(object_name=term)

    def create_label(self, term, entity_type):
        return _('There are currently no {object_name}s for this site').format(object_name=term)

_instances = {
    u'entity_type': None,
}

_bases = {
    u'entity_type': [EntityTypeTranslator]
}
