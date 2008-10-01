from ckan.commands import CommandBase

import ckan.model as model

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

        revision_objects = [ ckan.model.PackageRevision,
                ckan.models.PackageTagRevision ]
        to_purge = []
        for revobj in revision_objects:
            items = revobj.query.filter_by(revision=self.revision)
            for item in items:
                continuity = item.base
                how_many = revobj.query.filter_by(continuity=continuity).count()
                if how_many == 1:
                    to_purge.append(continuity)
                model.Session.delete(item)
        for item in to_purge:
            item.purge()
        if self.leave_record:
            self.revision.log_message = 'PURGED'
        else:
            model.Session.delete(self.revision)

        # now commit changes
        try:
            model.Session.commit()
        except:
            model.Session.rollback()
            model.Session.remove()

