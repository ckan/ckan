from ckan.lib.base import *

class CkanBaseController(BaseController):

    def __before__(self, action, **params):
        # what is different between session['user'] and environ['REMOTE_USER']
        c.user = request.environ.get('REMOTE_USER', None)
        c.remote_addr = request.environ.get('REMOTE_ADDR', 'Unknown IP Address')
        if c.remote_addr == 'localhost' or c.remote_addr == '127.0.0.1':
            # see if it was proxied
            c.remote_addr = request.environ.get('HTTP_X_FORWARDED_FOR',
                    '127.0.0.1')
        if c.user:
            c.author = c.user
        else:
            c.author = c.remote_addr

    def _list_page(self, registerName, id, templatePath):
        # Todo: Change to use Pylons webhelper Pagination classes.
        from ckan.misc import Paginate
        try:
            listIndex = int(id)
        except:
            listIndex = 0
        rev = self.repo.youngest_revision()
        register = getattr(rev.model, registerName)
        pager = Paginate(register)
        pager.setListIndex(listIndex)
        PageContextSetter(c, pager)
        c.register_name = registerName
        return render(templatePath)


class PageContextSetter(object):

    def __init__(self, c, pager):
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

