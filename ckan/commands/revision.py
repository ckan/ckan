from ckan.commands import CommandBase

import ckan.models

class PurgeRevision(CommandBase):
    '''Purge all changes associated with a revision.

    For the sake of having a record leave revision in existence but chagne
    log_message to "PURGED".
    '''

    def __init__(self, revision):
        super(PurgeRevision, self).__init__()
        self.revision = revision

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
        self.revision.log_message = 'PURGED'

