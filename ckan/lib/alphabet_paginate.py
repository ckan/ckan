'''
Based on webhelpers.paginator, but:
 * each page is for items beginning with a particular letter
 * output is suitable for Bootstrap

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
from itertools import dropwhile
import re

from sqlalchemy import  __version__ as sqav
from sqlalchemy.orm.query import Query
from webhelpers.html.builder import HTML
from routes import url_for


class AlphaPage(object):
    def __init__(self, collection, alpha_attribute, page, other_text, paging_threshold=50,
                controller_name='tag'):
        '''
        @param collection - sqlalchemy query of all the items to paginate
        @param alpha_attribute - name of the attribute (on each item of the
                             collection) which has the string to paginate by
        @param page - the page identifier - the start character or other_text
        @param other_text - the (i18n-ized) string for items with
                            non-alphabetic first character.
        @param paging_threshold - the minimum number of items required to
                              start paginating them.
        @param controller_name - The name of the controller that will be linked to,
                            which defaults to tag.  The controller name should be the
                            same as the route so for some this will be the full
                            controller name such as 'A.B.controllers.C:ClassName'
        '''
        self.collection = collection
        self.alpha_attribute = alpha_attribute
        self.page = page
        self.other_text = other_text
        self.paging_threshold = paging_threshold
        self.controller_name = controller_name

        self.letters = [char for char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'] + [self.other_text]
        
        # Work out which alphabet letters are 'available' i.e. have some results
        # because we grey-out those which aren't.
        self.available = dict( (c,0,) for c in self.letters )
        for c in self.collection:
            if isinstance(c, unicode):
                x = c[0]
            elif isinstance(c, dict):
                x = c[self.alpha_attribute][0]
            else:
                x = getattr(c, self.alpha_attribute)[0]
            x = x.upper()
            if x not in self.letters:
                x = self.other_text
            self.available[x] = self.available.get(x, 0) + 1

    def pager(self, q=None):
        '''Returns pager html - for navigating between the pages.
           e.g. Something like this:
             <ul class='pagination pagination-alphabet'>
                 <li class="active"><a href="/package/list?page=A">A</a></li>
                 <li><a href="/package/list?page=B">B</a></li>
                 <li><a href="/package/list?page=C">C</a></li>
                    ...
                 <li class="disabled"><a href="/package/list?page=Z">Z</a></li>
                 <li><a href="/package/list?page=Other">Other</a></li>
             </ul>
        '''
        if self.item_count < self.paging_threshold:
            return ''
        pages = []
        page = q or self.page
        for letter in self.letters:
            href = url_for(controller=self.controller_name, action='index', page=letter)
            link = HTML.a(href=href, c=letter)
            if letter != page:
                if self.available.get(letter, 0):
                    li_class = ''
                else:
                    li_class = 'disabled'
            else:
                li_class = 'active'
            attributes = {'class_': li_class} if li_class else {}
            page_element = HTML.li(link, **attributes)
            pages.append(page_element)
        ul = HTML.tag('ul', *pages)
        div = HTML.div(ul, class_='pagination pagination-alphabet')
        return div


    @property
    def items(self):
        '''Returns items on the current page.'''
        if isinstance(self.collection, Query):
            query = self.collection
            if sqav.startswith("0.4"):
                attribute = getattr(query.table.c,
                                    self.alpha_attribute)
            elif sqav.startswith("0.5"):
                 attribute = getattr(query._entity_zero().selectable.c,
                                     self.alpha_attribute)
            else:
                entity = getattr(query.column_descriptions[0]['expr'],
                                 self.alpha_attribute)
                query = query.add_columns(entity)
                column = dropwhile(lambda x: x['name'] != \
                                   self.alpha_attribute,
                                   query.column_descriptions)
                attribute = column.next()['expr']
            if self.item_count >= self.paging_threshold:
                if self.page != self.other_text:
                    query = query.filter(attribute.ilike(u'%s%%' % self.page))
                else:
                    # regexp search
                    query = query.filter(attribute.op('~')(u'^[^a-zA-Z].*'))
            query.order_by(attribute)
            return query.all()
        elif isinstance(self.collection,list):
            if self.item_count >= self.paging_threshold:
                if self.page != self.other_text:
                    if isinstance(self.collection[0], dict):
                        items = [x for x in self.collection if x[self.alpha_attribute][0:1].lower() == self.page.lower()]
                    elif isinstance(self.collection[0], unicode):
                        items = [x for x in self.collection if x[0:1].lower() == self.page.lower()]
                    else:
                        items = [x for x in self.collection if getattr(x,self.alpha_attribute)[0:1].lower() == self.page.lower()]
                else:
                    # regexp search
                    if isinstance(self.collection[0], dict):
                        items = [x for x in self.collection if re.match('^[^a-zA-Z].*',x[self.alpha_attribute])]
                    else:
                        items = [x for x in self.collection if re.match('^[^a-zA-Z].*',x)]
                items.sort()
            else:
                items = self.collection
            return items
        else:
            raise NotImplementedError

    @property
    def item_count(self):
        if isinstance(self.collection, Query):
            return self.collection.count()
        elif isinstance(self.collection,list):
            return len(self.collection)
        else:
            raise NotImplementedError
