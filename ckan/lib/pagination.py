# -*- coding: utf-8 -*-
u'''

This module was copied (with modifications) from the webhelpers library,
which is distributed with the following license:

Copyright (c) 2005-2009 Ben Bangert, James Gardner, Philip Jenvey,
                        Mike Orr, Jon Rosenbaugh, Christoph Haas,
                        and other contributors.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. The name of the author or contributors may not be used to endorse or
   promote products derived from this software without specific prior
   written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
SUCH DAMAGE.
'''
import re
from string import Template

import dominate.tags as tags
from markupsafe import Markup
from six import text_type
from six.moves import range


class BasePage(list):
    """A list/iterator of items representing one page in a larger
    collection.

    An instance of the "Page" class is created from a collection of things.
    The instance works as an iterator running from the first item to the
    last item on the given page. The collection can be:

    - a sequence
    - an SQLAlchemy query - e.g.: Session.query(MyModel)
    - an SQLAlchemy select - e.g.: sqlalchemy.select([my_table])

    A "Page" instance maintains pagination logic associated with each
    page, where it begins, what the first/last item on the page is, etc.
    The pager() method creates a link list allowing the user to go to
    other pages.

    **WARNING:** Unless you pass in an item_count, a count will be
    performed on the collection every time a Page instance is created.
    If using an ORM, it's advised to pass in the number of items in the
    collection if that number is known.

    Instance attributes:

    original_collection
        Points to the collection object being paged through

    item_count
        Number of items in the collection

    page
        Number of the current page

    items_per_page
        Maximal number of items displayed on a page

    first_page
        Number of the first page - starts with 1

    last_page
        Number of the last page

    page_count
        Number of pages

    items
        Sequence/iterator of items on the current page

    first_item
        Index of first item on the current page - starts with 1

    last_item
        Index of last item on the current page

    """

    def __init__(
        self,
        collection,
        page=1,
        items_per_page=20,
        item_count=None,
        sqlalchemy_session=None,
        presliced_list=False,
        url=None,
        **kwargs
    ):
        """Create a "Page" instance.

        Parameters:

        collection
            Sequence, SQLAlchemy select object or SQLAlchemy ORM-query
            representing the collection of items to page through.

        page
            The requested page number - starts with 1. Default: 1.

        items_per_page
            The maximal number of items to be displayed per page.
            Default: 20.

        item_count (optional)
            The total number of items in the collection - if known.
            If this parameter is not given then the paginator will count
            the number of elements in the collection every time a "Page"
            is created. Giving this parameter will speed up things.

        presliced_list (optional)
            Indicates whether the collection, when a list, has already
            been sliced for the current viewing page, and thus should
            *not* be sliced again.

        sqlalchemy_session (optional)
            If you want to use an SQLAlchemy (0.4) select object as a
            collection then you need to provide an SQLAlchemy session object.
            Select objects do not have a database connection attached so it
            would not be able to execute the SELECT query.

        url (optional)
            A URL generator function. See module docstring for details.
            This is used only by ``.pager()``.

        Further keyword arguments are used as link arguments in the pager().
        """
        self._url_generator = url

        # Safe the kwargs class-wide so they can be used in the pager() method
        self.kwargs = kwargs

        # Save a reference to the collection
        self.original_collection = collection

        self.collection = collection

        # The self.page is the number of the current page.
        # The first page has the number 1!
        try:
            self.page = int(page)  # make it int() if we get it as a string
        except (ValueError, TypeError):
            self.page = 1

        self.items_per_page = items_per_page

        # Unless the user tells us how many items the collections has
        # we calculate that ourselves.
        if item_count is not None:
            self.item_count = item_count
        else:
            self.item_count = len(self.collection)

        # Compute the number of the first and last available page
        if self.item_count > 0:
            self.first_page = 1
            self.page_count = int(
                ((self.item_count - 1) / self.items_per_page) + 1)
            self.last_page = self.first_page + self.page_count - 1

            # Make sure that the requested page number is the range of
            # valid pages
            if self.page > self.last_page:
                self.page = self.last_page
            elif self.page < self.first_page:
                self.page = self.first_page

            # Note: the number of items on this page can be less than
            #       items_per_page if the last page is not full
            self.first_item = (self.page - 1) * items_per_page + 1
            self.last_item = min(
                self.first_item + items_per_page - 1, self.item_count
            )

            # We subclassed "list" so we need to call its init() method
            # and fill the new list with the items to be displayed on the page.
            # We use list() so that the items on the current page are retrieved
            # only once. Otherwise it would run the actual SQL query everytime
            # .items would be accessed.
            if presliced_list:
                self.items = self.collection
            else:
                first = self.first_item - 1
                last = self.last_item
                self.items = list(self.collection[first:last])

            # Links to previous and next page
            if self.page > self.first_page:
                self.previous_page = self.page - 1
            else:
                self.previous_page = None

            if self.page < self.last_page:
                self.next_page = self.page + 1
            else:
                self.next_page = None

        # No items available
        else:
            self.first_page = None
            self.page_count = 0
            self.last_page = None
            self.first_item = None
            self.last_item = None
            self.previous_page = None
            self.next_page = None
            self.items = []

        # This is a subclass of the 'list' type. Initialise the list now.
        list.__init__(self, self.items)

    def __repr__(self):
        return (
            u"Page:\n"
            u"Collection type:  %(type)s\n"
            u"(Current) page:   %(page)s\n"
            u"First item:       %(first_item)s\n"
            u"Last item:        %(last_item)s\n"
            u"First page:       %(first_page)s\n"
            u"Last page:        %(last_page)s\n"
            u"Previous page:    %(previous_page)s\n"
            u"Next page:        %(next_page)s\n"
            u"Items per page:   %(items_per_page)s\n"
            u"Number of items:  %(item_count)s\n"
            u"Number of pages:  %(page_count)s\n"
            % {
                u"type": type(self.collection),
                u"page": self.page,
                u"first_item": self.first_item,
                u"last_item": self.last_item,
                u"first_page": self.first_page,
                u"last_page": self.last_page,
                u"previous_page": self.previous_page,
                u"next_page": self.next_page,
                u"items_per_page": self.items_per_page,
                u"item_count": self.item_count,
                u"page_count": self.page_count,
            }
        )

    def pager(
        self,
        format=u"~2~",
        page_param=u"page",
        partial_param=u"partial",
        show_if_single_page=False,
        separator=u" ",
        onclick=None,
        symbol_first=u"<<",
        symbol_last=u">>",
        symbol_previous=u"<",
        symbol_next=u">",
        link_attr={u"class": u"pager_link"},
        curpage_attr={u"class": u"pager_curpage"},
        dotdot_attr={u"class": u"pager_dotdot"},
        **kwargs
    ):
        """Return string with links to other pages (e.g. "1 2 [3] 4 5 6 7").

        format:
            Format string that defines how the pager is rendered. The string
            can contain the following $-tokens that are substituted by the
            string.Template module:

            - $first_page: number of first reachable page
            - $last_page: number of last reachable page
            - $page: number of currently selected page
            - $page_count: number of reachable pages
            - $items_per_page: maximal number of items per page
            - $first_item: index of first item on the current page
            - $last_item: index of last item on the current page
            - $item_count: total number of items
            - $link_first: link to first page (unless this is first page)
            - $link_last: link to last page (unless this is last page)
            - $link_previous: link to previous page (unless this is first page)
            - $link_next: link to next page (unless this is last page)

            To render a range of pages the token '~3~' can be used. The
            number sets the radius of pages around the current page.
            Example for a range with radius 3:

            '1 .. 5 6 7 [8] 9 10 11 .. 500'

            Default: '~2~'

        symbol_first
            String to be displayed as the text for the %(link_first)s
            link above.

            Default: '<<'

        symbol_last
            String to be displayed as the text for the %(link_last)s
            link above.

            Default: '>>'

        symbol_previous
            String to be displayed as the text for the %(link_previous)s
            link above.

            Default: '<'

        symbol_next
            String to be displayed as the text for the %(link_next)s
            link above.

            Default: '>'

        separator:
            String that is used to separate page links/numbers in the
            above range of pages.

            Default: ' '

        page_param:
            The name of the parameter that will carry the number of the
            page the user just clicked on. The parameter will be passed
            to a url_for() call so if you stay with the default
            ':controller/:action/:id' routing and set page_param='id' then
            the :id part of the URL will be changed. If you set
            page_param='page' then url_for() will make it an extra
            parameters like ':controller/:action/:id?page=1'.
            You need the page_param in your action to determine the page
            number the user wants to see. If you do not specify anything
            else the default will be a parameter called 'page'.

            Note: If you set this argument and are using a URL generator
            callback, the callback must accept this name as an argument instead
            of 'page'.
            callback, becaust the callback requires its argument to be 'page'.
            Instead the callback itself can return any URL necessary.

        partial_param:
            When using AJAX/AJAH to do partial updates of the page area the
            application has to know whether a partial update (only the
            area to be replaced) or a full update (reloading the whole
            page) is required. So this parameter is the name of the URL
            parameter that gets set to 1 if the 'onclick' parameter is
            used. So if the user requests a new page through a Javascript
            action (onclick) then this parameter gets set and the application
            is supposed to return a partial content. And without
            Javascript this parameter is not set. The application thus has
            to check for the existence of this parameter to determine
            whether only a partial or a full page needs to be returned.
            See also the examples in this modules docstring.

            Default: 'partial'

            Note: If you set this argument and are using a URL generator
            callback, the callback must accept this name as an argument instead
            of 'partial'.

        show_if_single_page:
            if True the navigator will be shown even if there is only
            one page

            Default: False

        link_attr (optional)
            A dictionary of attributes that get added to A-HREF links
            pointing to other pages. Can be used to define a CSS style
            or class to customize the look of links.

            Example: { 'style':'border: 1px solid green' }

            Default: { 'class':'pager_link' }

        curpage_attr (optional)
            A dictionary of attributes that get added to the current
            page number in the pager (which is obviously not a link).
            If this dictionary is not empty then the elements
            will be wrapped in a SPAN tag with the given attributes.

            Example: { 'style':'border: 3px solid blue' }

            Default: { 'class':'pager_curpage' }

        dotdot_attr (optional)
            A dictionary of attributes that get added to the '..' string
            in the pager (which is obviously not a link). If this
            dictionary is not empty then the elements will be wrapped in
            a SPAN tag with the given attributes.

            Example: { 'style':'color: #808080' }

            Default: { 'class':'pager_dotdot' }

        onclick (optional)
            This paramter is a string containing optional Javascript
            code that will be used as the 'onclick' action of each
            pager link.  It can be used to enhance your pager with
            AJAX actions loading another page into a DOM object.

            In this string the variable '$partial_url' will be replaced by
            the URL linking to the desired page with an added 'partial=1'
            parameter (or whatever you set 'partial_param' to).
            In addition the '$page' variable gets replaced by the
            respective page number.

            Note that the URL to the destination page contains a
            'partial_param' parameter so that you can distinguish
            between AJAX requests (just refreshing the paginated area
            of your page) and full requests (loading the whole new
            page).

            [Backward compatibility: you can use '%s' instead of
            '$partial_url']

            jQuery example:
                "$('#my-page-area').load('$partial_url'); return false;"

            Yahoo UI example:
                "YAHOO.util.Connect.asyncRequest('GET','$partial_url',{
                    success:function(o){
                        YAHOO.util.Dom.get(
                            '#my-page-area'
                        ).innerHTML=o.responseText;
                    }
                },null); return false;"

            scriptaculous example:
                "new Ajax.Updater('#my-page-area', '$partial_url',
                    {asynchronous:true, evalScripts:true}); return false;"

            ExtJS example:
                "Ext.get('#my-page-area').load({url:'$partial_url'});
                return false;"

            Custom example:
                "my_load_page($page)"

        Additional keyword arguments are used as arguments in the links.
        Otherwise the link will be created with url_for() which points
        to the page you are currently displaying.

        """
        self.curpage_attr = curpage_attr
        self.separator = separator
        self.pager_kwargs = kwargs
        self.page_param = page_param
        self.partial_param = partial_param
        self.onclick = onclick
        self.link_attr = link_attr
        self.dotdot_attr = dotdot_attr

        # Don't show navigator if there is no more than one page
        if self.page_count == 0 or (
            self.page_count == 1 and not show_if_single_page
        ):
            return u""

        # Replace ~...~ in token format by range of pages
        result = re.sub(u"~(\\d+)~", self._range, format)

        # Interpolate '%' variables
        result = Template(result).safe_substitute(
            {
                u"first_page": self.first_page,
                u"last_page": self.last_page,
                u"page": self.page,
                u"page_count": self.page_count,
                u"items_per_page": self.items_per_page,
                u"first_item": self.first_item,
                u"last_item": self.last_item,
                u"item_count": self.item_count,
                u"link_first": self.page > self.first_page
                and self._pagerlink(self.first_page, symbol_first)
                or u"",
                u"link_last": self.page < self.last_page
                and self._pagerlink(self.last_page, symbol_last)
                or u"",
                u"link_previous": self.previous_page
                and self._pagerlink(self.previous_page, symbol_previous)
                or u"",
                u"link_next": self.next_page
                and self._pagerlink(self.next_page, symbol_next)
                or u"",
            }
        )

        return Markup(result)

    # Private methods
    def _range(self, regexp_match):
        """
        Return range of linked pages (e.g. '1 2 [3] 4 5 6 7 8').

        Arguments:

        regexp_match
            A "re" (regular expressions) match object containing the
            radius of linked pages around the current page in
            regexp_match.group(1) as a string

        This function is supposed to be called as a callable in
        re.sub.

        """
        radius = int(regexp_match.group(1))

        # Compute the first and last page number within the radius
        # e.g. '1 .. 5 6 [7] 8 9 .. 12'
        # -> leftmost_page  = 5
        # -> rightmost_page = 9
        leftmost_page = max(self.first_page, (self.page - radius))
        rightmost_page = min(self.last_page, (self.page + radius))

        nav_items = []

        # Create a link to the first page (unless we are on the first page
        # or there would be no need to insert '..' spacers)
        if self.page != self.first_page and self.first_page < leftmost_page:
            nav_items.append(self._pagerlink(self.first_page, self.first_page))

        # Insert dots if there are pages between the first page
        # and the currently displayed page range
        if leftmost_page - self.first_page > 1:
            # Wrap in a SPAN tag if nolink_attr is set
            text = u".."
            if self.dotdot_attr:
                text = Markup(tags.span(text, **self.dotdot_attr))
            nav_items.append(text)

        for thispage in range(leftmost_page, rightmost_page + 1):
            # Hilight the current page number and do not use a link
            if thispage == self.page:
                text = u"%s" % (thispage,)
                # Wrap in a SPAN tag if nolink_attr is set
                if self.curpage_attr:
                    text = Markup(tags.span(text, **self.curpage_attr))
                nav_items.append(text)
            # Otherwise create just a link to that page
            else:
                text = u"%s" % (thispage,)
                nav_items.append(self._pagerlink(thispage, text))

        # Insert dots if there are pages between the displayed
        # page numbers and the end of the page range
        if self.last_page - rightmost_page > 1:
            text = u".."
            # Wrap in a SPAN tag if nolink_attr is set
            if self.dotdot_attr:
                text = Markup(tags.span(text, **self.dotdot_attr))
            nav_items.append(text)

        # Create a link to the very last page (unless we are on the last
        # page or there would be no need to insert '..' spacers)
        if self.page != self.last_page and rightmost_page < self.last_page:
            nav_items.append(self._pagerlink(self.last_page, self.last_page))

        return self.separator.join(nav_items)

    def _pagerlink(self, page, text):
        """
        Create a URL that links to another page using url_for().

        Parameters:

        page
            Number of the page that the link points to

        text
            Text to be printed in the A-HREF tag
        """
        link_params = {}
        # Use the instance kwargs from Page.__init__ as URL parameters
        link_params.update(self.kwargs)
        # Add keyword arguments from pager() to the link as parameters
        link_params.update(self.pager_kwargs)
        link_params[self.page_param] = page

        # Get the URL generator
        if self._url_generator is not None:
            url_generator = self._url_generator
        else:
            from ckan.lib.helpers import pager_url

        # Create the URL to load a certain page
        link_url = url_generator(**link_params)

        if self.onclick:  # create link with onclick action for AJAX
            # Create the URL to load the page area part of a certain page (AJAX
            # updates)
            link_params[self.partial_param] = 1
            partial_url = url_generator(**link_params)
            try:
                # if '%s' is used in the 'onclick' parameter
                # (backwards compatibility)
                onclick_action = self.onclick % (partial_url,)
            except TypeError:
                onclick_action = Template(self.onclick).safe_substitute(
                    {u"partial_url": partial_url, u"page": page}
                )
            return tags.a(
                text, href=link_url, onclick=onclick_action, **self.link_attr
            )
        else:  # return static link
            return tags.a(text, href=link_url, **self.link_attr)


class Page(BasePage):
    def pager(self, *args, **kwargs):
        with tags.div(cls=u"pagination-wrapper") as wrapper:
            tags.ul(u"$link_previous ~2~ $link_next", cls=u"pagination")
        params = dict(
            format=text_type(wrapper),
            symbol_previous=u"«",
            symbol_next=u"»",
            curpage_attr={u"class": u"active"},
            link_attr={},
        )
        params.update(kwargs)
        return super(Page, self).pager(*args, **params)

    # Put each page link into a <li> (for Bootstrap to style it)

    def _pagerlink(self, page, text, extra_attributes=None):
        anchor = super(Page, self)._pagerlink(page, text)
        extra_attributes = extra_attributes or {}
        return text_type(tags.li(anchor, **extra_attributes))

    # Change 'current page' link from <span> to <li><a>
    # and '..' into '<li><a>..'
    # (for Bootstrap to style them properly)

    def _range(self, regexp_match):
        html = super(Page, self)._range(regexp_match)
        # Convert ..
        dotdot = u'<span class="pager_dotdot">..</span>'
        dotdot_link = tags.li(tags.a(u"...", href=u"#"), cls=u"disabled")
        html = re.sub(dotdot, text_type(dotdot_link), html)

        # Convert current page
        text = u"%s" % self.page
        current_page_span = text_type(tags.span(text, **self.curpage_attr))
        current_page_link = self._pagerlink(
            self.page, text, extra_attributes=self.curpage_attr
        )
        return re.sub(current_page_span, current_page_link, html)
