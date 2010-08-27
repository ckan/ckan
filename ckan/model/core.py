from meta import *
import vdm.sqlalchemy

from domain_object import DomainObject

## VDM-specific tables
revision_table = vdm.sqlalchemy.make_revision_table(metadata)

class System(DomainObject):
    def __str__(self):
        return 'System'
    def purge(self):
        pass

# VDM-specific domain objects
State = vdm.sqlalchemy.State
State.all = [ State.ACTIVE, State.DELETED ]
Revision = vdm.sqlalchemy.make_Revision(mapper, revision_table)




