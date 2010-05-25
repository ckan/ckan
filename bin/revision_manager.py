class RevisionManager(object):
    '''Revision manager
    * Keep track of revisions and changes inside a loop.
    * Group a bunch of changes into one revision.
    '''
    def __init__(self, change_message, changes_per_commit=10):
        self.change_message = unicode(change_message)
        self.num_changes_since_commit = 0
        self.changes_per_commit = changes_per_commit
        from ckan import model
        self.Session = model.Session

    def _revision_changes(self):
        return self.Session.new or self.Session.dirty

    def before_change(self):
        '''Call this before a change to a revisioned object'''
        if self.num_changes_since_commit == 0:
            assert not self._revision_changes()
            from ckan import model
            self.rev = model.repo.new_revision() 
            self.rev.author = u'auto-edit'
            if self.change_message:
                self.rev.message = self.change_message
        self.num_changes_since_commit += 1

    def after_change(self, force_commit=False):
        '''Call this after a change to a revisioned object. Should be
        same number of after_change calls as before_change'''
        its_about_time = self.num_changes_since_commit >= self.changes_per_commit
        if its_about_time:
            assert self._revision_changes()
        if force_commit or its_about_time:
            from ckan import model
            model.Session.commit()
            self.num_changes_since_commit = 0
        
    def finished(self):
        '''Call this after all changes'''
        if self.num_changes_since_commit:
            self.after_change(force_commit=True)
        from ckan import model
        model.Session.remove()
