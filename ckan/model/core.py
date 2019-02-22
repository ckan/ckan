# encoding: utf-8

import datetime

import domain_object
import meta
import vdm.sqlalchemy
from sqlalchemy import Column, DateTime, Text, Boolean


__all__ = ['System', 'State']


class System(domain_object.DomainObject):

    name = 'system'

    def __unicode__(self):
        return u'<%s>' % self.__class__.__name__

    def purge(self):
        pass

    @classmethod
    def by_name(cls, name):
        return System()


# VDM-specific domain objects
State = vdm.sqlalchemy.State
State.all = [State.ACTIVE, State.DELETED]
