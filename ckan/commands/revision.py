from ckan.commands import CommandBase

import ckan.models

class PurgeRevision(CommandBase):
    '''Purge all changes associated with a revision.

    If leave_record is True leave revision in existence but change
    log_message to "PURGED", and otherwise delete revision object as well.
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

        revision_objects = [ ckan.models.PackageRevision,
                ckan.models.TagRevision, ckan.models.PackageTagRevision
                ]
        to_purge = []
        for revobj in revision_objects:
            items = revobj.selectBy(revision=self.revision)
            for item in items:
                continuity = item.base
                how_many = revobj.selectBy(base=continuity).count()
                if how_many == 1:
                    to_purge.append(continuity)
                revobj.delete(item.id)
        for item in to_purge:
            item.purge()
        if self.leave_record:
            self.revision.log_message = 'PURGED'
        else:
            # TODO
            # need to do some work to upate dependent revisions
            # because of reference in base_revision
            # get next lowest revision 
            referring_revisions = ckan.models.Revision.selectBy(base_revisionID=self.revision.id)
            # get next lowest revision
            all = ckan.models.Revision.select(ckan.models.Revision.q.id <
                    self.revision.id, orderBy=-ckan.models.Revision.q.id)
            first = None
            for rev in all:
                first = rev
                break
            print 'First below, current revision', first.id, self.revision.id
            for rev in referring_revisions:
                rev.base_revision = first
            self.revision.__class__.delete(self.revision.id)

