from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController

class TagController(CkanBaseController):
    repo = model.repo

    def index(self):
        return render_response('tag/index')

    def read(self, id):
        try:
            rev = self.repo.youngest_revision()
            c.tag = rev.model.tags.get(id)
        except:
            abort(404)
        return render_response('tag/read')

    def list(self):
        rev = self.repo.youngest_revision()
        tags = rev.model.tags
        c.tag_count = len(tags)
        c.tags = tags
        return render_response('tag/list')

