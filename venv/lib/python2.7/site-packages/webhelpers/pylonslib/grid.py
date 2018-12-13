"""
This module is DEPRECATED. Please use ``webhelpers.html.grid`` in new
applications. Support for paged grids has been added to that module in a
framework-neutral way.

PYRAMID USERS: This implementation is incompatible with Pyramid. Use
``webhelpers.html.grid`` instead.
"""


from webhelpers.html.builder import HTML, literal
import webhelpers.html.grid as grid
from webhelpers.misc import deprecate

class NoRequestError(Exception):
    pass

class PylonsGrid(grid.Grid):
    """
    Subclass of Grid that can handle header link generation for quick building
    of tables that support ordering of their contents, paginated results etc.
    """
    
    def __init__(self, request, *args, **kw):
        deprecate("please migrate to webhelpers.html.grid")
        self.request = request
        super(PylonsGrid, self).__init__(*args, **kw)
    
    def generate_header_link(self, column_number, column, label_text):
        """ This handles generation of link and then decides to call
        self.default_header_ordered_column_format 
        or 
        self.default_header_column_format 
        based on if current column is the one that is used for sorting or not
        """ 
        from pylons import url
        # this will handle possible URL generation
        request_copy = dict(self.request.copy().GET) 
        self.order_column = request_copy.pop("order_col", None)
        self.order_dir = request_copy.pop("order_dir", None)
        
        if column == self.order_column and self.order_dir == "asc":
            new_order_dir = "dsc"
        else:
            new_order_dir = "asc"
        
        url_href = url.current(order_col=column, order_dir=new_order_dir,
                               **request_copy)
        label_text = HTML.tag("a", href=url_href, c=label_text)
        # Is the current column the one we're ordering on?
        if column == self.order_column:
            return self.default_header_ordered_column_format(column_number,
                                                             column,
                                                             label_text)
        else:
            return self.default_header_column_format(column_number, column,
                                                     label_text)

class PylonsObjectGrid(PylonsGrid):
    """ This grid will work well with sqlalchemy row instances """
    def default_column_format(self, column_number, i, record, column_name):
        class_name = "c%s" % (column_number)
        return HTML.tag("td", getattr(record, column_name), class_=class_name)
