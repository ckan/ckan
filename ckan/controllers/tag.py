from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController
from ckan.misc import Paginate

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

    def page(self, id):
        try:
            listIndex = int(id)
        except:
            listIndex = 0
        #print "List index: %s" % listIndex
        rev = self.repo.youngest_revision()
        pager = Paginate(rev.model.tags)
        pager.setListIndex(listIndex)
        c.is_single_page = pager.isSinglePage()
        c.list_index = pager.listIndex
        c.list_length = pager.getListLength()
        c.has_previous = pager.hasPrevious()
        c.previous_index = pager.getPrevious()
        c.has_next = pager.hasNext()
        c.next_index = pager.getNext()
        c.pages_list = pager.getPagesList()
        c.page_list = pager.getPageList()
        c.page_range = pager.getPageListIndexRange()
        return render('tag/page')

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


