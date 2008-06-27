from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController

import ckan.authz
import ckan.commands.revision

class RevisionController(CkanBaseController):

    def index(self):
        return self.list()

    def list(self, id=0):
        c.show_purge_links = self._has_purge_permissions()
        return self._paginate_list('revisions', id, 'revision/list')

    def read(self, id=None):
        if id is None:
            h.redirect_to(controller='revision', action='list')
        id = int(id)
        c.revision = model.repo.get_revision(id)
        pkgs = model.PackageRevision.selectBy(revision=c.revision)
        c.packages = [ pkg.base for pkg in pkgs ]
        tags = model.TagRevision.selectBy(revision=c.revision)
        c.tags = [ tag.base for tag in tags ]
        pkgtags = model.PackageTagRevision.selectBy(revision=c.revision)
        c.pkgtags = [ pkgtag.base for pkgtag in pkgtags ]
        return render('revision/read')

    def _has_purge_permissions(self):
        authorizer = ckan.authz.Authorizer()
        action = ckan.authz.actions['revision-purge']
        return ( c.user and authorizer.is_authorized(c.user, action) )

    def purge(self, id=None):
        if id is None:
            c.error = 'No revision id specified'
            return render('revision/purge')
        if not self._has_purge_permissions():
            c.error = 'You are not authorized to perform this action'
            return render('revision/purge')
        else:
            revision = model.repo.get_revision(id)
            cmd = ckan.commands.revision.PurgeRevision(revision)
            try:
                cmd.execute()
            except Exception, inst:
                # is this a security risk?
                # probably not because only admins get to here
                c.error = 'Purge of revision failed: %s' % inst
            return render('revision/purge')

