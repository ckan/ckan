from sqlalchemy.orm import class_mapper

from ckan.commands import CommandBase

import ckan.model as model

class PurgeRevision(CommandBase):
    '''Purge all changes associated with a revision.

    If leave_record is True leave revision in existence but change
    message to "PURGED", and otherwise delete revision object as well.
    '''

    def __init__(self, revision, leave_record=True):
        super(PurgeRevision, self).__init__()
        self.revision = revision
        self.leave_record = leave_record

    def execute(self):
        # list everything affected by this transaction
        # check continuity objects and cascade on everything else ?
        # crudely get all object revisions associated with this
        # then check whether this is the only revision and delete the
        # continuity object

        # alternatively delete all associated object revisions\
        # then do a select on continutity to check which have zero associated
        # revisions (should only be these ...)

        print 'id:', self.revision.id
        revision_objects = [ model.PackageRevision,
                model.PackageTagRevision ]
        to_purge = []
        for revobj in revision_objects:
            items = revobj.query.filter_by(revision=self.revision)
            for item in items:
                continuity = item.continuity
                if continuity.revision == self.revision:
                    trevobjs = revobj.query.filter_by(
                            continuity=continuity
                            ).order_by(revobj.c.revision_id.desc()).limit(2).all()
                    if len(trevobjs) == 0:
                        raise Exception('Should have at least one revision.')
                    if len(trevobjs) == 1:
                        to_purge.append(continuity)
                    else:
                        new_correct_revobj = trevobjs[1] # older one
                        print new_correct_revobj
                        # revert continuity object back to original version
                        table = class_mapper(continuity.__class__).mapped_table
                        # TODO: ? this will only set columns and not mapped attribs
                        # TODO: need to do this directly on table or disable
                        # revisioning behaviour ...
                        for key in table.c.keys():
                            value = getattr(new_correct_revobj, key)
                            print key, value
                            print 'old:', getattr(continuity, key)
                            setattr(continuity, key, value)
                model.Session.delete(item)
        for item in to_purge:
            item.purge()
        if self.leave_record:
            self.revision.message = 'PURGED'
        else:
            model.Session.delete(self.revision)

        # now commit changes
        try:
            model.Session.commit()
        except:
            model.Session.rollback()
            model.Session.remove()
            raise

