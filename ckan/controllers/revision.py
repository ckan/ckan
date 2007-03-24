from ckan.lib.base import *

class RevisionController(BaseController):

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
        return render_response('revision/read')

