# -*- coding: utf-8 -*-

import logging
from ckan.common import _

log = logging.getLogger(__name__)


def reset_humanizers():
    for k in _instances:
        _instances[k] = None

    # First base will always be provided by current module. We want to
    # keep it as fallback
    for k, v in _bases.items():
        _bases[k] = v[:1]


def add_humanizer(humanizer_type, cls):
    """Add custom class to humanizers hierarchy.

    Class must be inherited from
    :py:class:`~ckan.lib.humanize.BaseHumanizer`. Every time
    ``h.humanize_entity_type`` is called, its third argument `purpose`
    will be converted to method name by replacing all whitespaces with
    underscore. If corresponding method exists in humanizer instance,
    it will be used for obtaining required message.

    Example::

      class LinkHumanizer(BaseHumanizer):
          def add_link(self, term, entity_type):
              # term: custom group/org/package type, i.e, `camel-photos`
              # entity_type: native entity name, i.e, `organization`,
              # `group`, `dataset`.
              return _("Create new %s" % term)

      class ExtPlugin(p.SingletonPlugin):
          p.implements(p.IConfigure)
          def update_config(self, config_):
              tk.add_humanizer('entity_type', LinkHumanizer)

      # will be used in following case
      h.humanize_entity_type('group', 'custom_group', 'add link')

    :param humanizer_type: defines type of conversions performed by
        humanizer. At the moment only ``entity_type`` supported.
    :type humanizer_type: string

    :param cls: Class that extends :py:class:`~ckan.lib.humanize.BaseHumanizer`
    :type cls: class

    """
    _bases[humanizer_type].append(cls)


def get_humanizer(type_, **kwargs):
    if not _instances[type_]:
        _instances[type_] = type(type_, tuple(reversed(_bases[type_])), kwargs)()
    return _instances[type_]


class BaseHumanizer(object):
    def _prepare_term(self, term):
        return term.replace(u"_", u" ").capitalize()

    def _default(self, term, **kwargs):
        # Use default value from template
        return

    def __call__(self, purpose, term, *args, **kwargs):
        handler = getattr(self, purpose.replace(u" ", u"_"), None)
        term = self._prepare_term(term)
        if handler:
            return handler(term, *args, **kwargs)
        log.debug(u'%s has no handlers for "%s"', self.__class__, purpose)
        return self._default(term, **kwargs)


class EntityTypeHumanizer(BaseHumanizer):
    def add_link(self, term, entity_type):
        return _(u"Add {}".format(term))

    def breadcrumb(self, term, entity_type):
        return _(u"{}s".format(term))

    def facet_label(self, term, entity_type):
        return _(u"{}s".format(term))

    def page_title(self, term, entity_type):
        return _(u"{}s".format(term))

    def main_nav(self, term, entity_type):
        return _(u"{}s".format(term))

    def create_title(self, term, entity_type):
        return _(u"Create {}".format(term))

    def content_tab(self, term, entity_type):
        return _(u"{}s".format(term))

    def default_label(self, term, entity_type):
        return _(u"{}".format(term))

    def no_label(self, term, entity_type):
        return _(u"No {}".format(term))

    def form_label(self, term, entity_type):
        return _(u"{} Form".format(term))

    def edit_label(self, term, entity_type):
        return _(u"Edit {}".format(term))

    def update_label(self, term, entity_type):
        return _(u"Update {}".format(term))

    def create_label(self, term, entity_type):
        return _(u"Create {}".format(term))

    def save_label(self, term, entity_type):
        return _(u"Save {}".format(term))

    def sidebar_label(self, term, entity_type):
        return _(u"{}".format(term))

    def my_label(self, term, entity_type):
        return _(u"My {}s".format(term))

    def create_label(self, term, entity_type):
        return _(u"There are currently no {}s for this site".format(term))

    def description_placeholder(self, term, entity_type):
        return _(u"A little information about my {}...".format(term))


_instances = {
    u"entity_type": None,
}

_bases = {u"entity_type": [EntityTypeHumanizer]}
