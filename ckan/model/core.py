from meta import metadata, mapper
from sqlalchemy import Column, ForeignKey, DateTime, Text, orm
import vdm.sqlalchemy

from domain_object import DomainObject

## VDM-specific tables
revision_table = vdm.sqlalchemy.make_revision_table(metadata)

class System(DomainObject):
    
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
State.all = [ State.ACTIVE, State.DELETED ]
Revision = vdm.sqlalchemy.make_Revision(mapper, revision_table)


def make_revisioned_table(table):
    revision_table = vdm.sqlalchemy.make_revisioned_table(table)
    revision_table.append_column(Column('expired_id', 
                                 Text))
    revision_table.append_column(Column('revision_timestamp', DateTime))
    revision_table.append_column(Column('expired_timestamp', DateTime, 
                                 default='9999-12-31'))
    return revision_table

