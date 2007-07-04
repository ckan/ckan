from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController

class RevisionController(CkanBaseController):

    def index(self):
        return self.list()

    def list(self):
        c.revisions = model.repo.history()
        return render_response('revision/list')

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
        return render_response('revision/read')

