# encoding: utf-8

from ckan.model import domain_object


class System(domain_object.DomainObject):

    name = u'system'

    def __unicode__(self):
        return u'<%s>' % self.__class__.__name__

    def purge(self):
        pass

    @classmethod
    def by_name(cls, name):
        return System()
