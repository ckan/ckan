from ckan.lib.base import *

class RevisionController(BaseController):
    def index(self):
        c.revisions = model.repo.history()
        return render_response('revision/list')
