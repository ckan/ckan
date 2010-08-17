'''
Based on webhelpers.paginator, but each page is for items beginning
 with a particular letter.

 Example:
        c.page = h.Page(
            collection=query,
            page=request.params.get('page', 'A'),
        )
    Template:            
        ${c.page.pager()}
        ${package_list(c.page.items)}
        ${c.page.pager()}
'''

from sqlalchemy.orm.query import Query
from pylons.i18n import _
from webhelpers.html.builder import HTML
from routes import url_for

class AlphaPage(object):
    def __init__(self, collection, alpha_attribute, page, other_text, paging_threshold=50):
        '''
        @param collection - sqlalchemy query of all the items to paginate
        @param alpha_attribute - name of the attribute (on each item of the
                             collection) which has the string to paginate by
        @param page - the page identifier - the start character or other_text
        @param other_text - the (i18n-ized) string for items with
                            non-alphabetic first character.
        @param paging_threshold - the minimum number of items required to
                              start paginating them.
        '''
        self.collection = collection
        self.alpha_attribute = alpha_attribute
        self.page = page
        self.other_text = other_text
        self.paging_threshold = paging_threshold
        

    def pager(self, q=None):
        '''Returns pager html - for navigating between the pages.
           e.g. Something like this:
             <div class='pager'>
                 <span class="pager_curpage">A</span>
                 <a class="pager_link" href="/package/list?page=B">B</a>
                 <a class="pager_link" href="/package/list?page=C">C</a>
                    ...
                 <a class="pager_link" href="/package/list?page=Z">Z</a
                 <a class="pager_link" href="/package/list?page=Other">Other</a
             </div>
        '''
        if self.item_count < self.paging_threshold:
            return ''
        pages = []
        page = q or self.page
        letters = [char for char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'] + [self.other_text]
        for letter in letters:
            if letter != page:
                page = HTML.a(class_='pager_link', href=url_for(page=letter), c=letter)
            else:
                page = HTML.span(class_='pager_curpage', c=letter)
            pages.append(page)                           
        div = HTML.tag('div', class_='pager', *pages)
        return div


    @property
    def items(self):
        '''Returns items on the current page.'''
        if isinstance(self.collection, Query):
            query = self.collection
            attribute = getattr(query.table.c, self.alpha_attribute)
            if self.item_count >= self.paging_threshold:
                if self.page != self.other_text:
                    query = query.filter(attribute.ilike(u'%s%%' % self.page))
                else:
                    # regexp search
                    query = query.filter(attribute.op('~')(u'^[^a-zA-Z].*'))
            query.order_by(attribute)
            return query.all()                                   
        else:
            raise NotImplementedError

    @property
    def item_count(self):
        if isinstance(self.collection, Query):
            return self.collection.count()
        else:
            raise NotImplementedError
