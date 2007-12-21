from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController

class TagController(CkanBaseController):
    repo = model.repo

    def index(self):
        return render('tag/index')

    def read(self, id):
        try:
            rev = self.repo.youngest_revision()
            c.tag = rev.model.tags.get(id)
        except:
            abort(404)
        return render('tag/read')

    def list(self):
        rev = self.repo.youngest_revision()
        tags = rev.model.tags
        c.tag_count = len(tags)
        c.tags = tags
        return render('tag/list')

    def search(self):
        c.search_terms = request.params.get('search_terms', '')
        if c.search_terms:
            c.tags = list(model.Tag.search_by_name(c.search_terms))
            c.tag_count = len(c.tags)
        return render('tag/search')
