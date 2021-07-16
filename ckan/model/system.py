# encoding: utf-8

from ckan.model import domain_object


class System(domain_object.DomainObject):

    name = 'system'

    def __unicode__(self):
        return '<%s>' % self.__class__.__name__

    def purge(self):
        pass

    @classmethod
    def by_name(cls, name):
        return System()
