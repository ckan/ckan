"""A helper to make an HTML table from a list of dicts, objects, or sequences.

A set of CSS styles complementing this helper is in
"webhelpers/html/public/stylesheets/grid.css". To use them, include the 
stylesheet in your applcation and set your <table> class to "stylized".

The documentation below is not very clear. This is a known bug. We need a
native English speaker who uses the module to volunteer to rewrite it.

This module is written and maintained by Ergo^.
"""

from webhelpers.html.builder import HTML, literal

class Grid(object):
    """
    This class is designed to aid programmer in the task of creation of
    tables/grids - structures that are mostly built from datasets.
    
    To create a grid at minimum one one needs to pass a dataset,
    like a list of dictionaries, or sqlalchemy proxy or query object::
    
        grid = Grid(itemlist, ['_numbered','c1', 'c2','c4'])

    where itemlist in this simple scenario is a list of dicts:

        [{'c1':1,'c2'...}, {'c1'...}, ...]
    
    This helper also received the list that defines order in which
    columns will be rendered - also keep note of special column name that can be
    passed in list that defines order - ``_numbered`` - this adds additional
    column that shows the number of item. For paging sql data there one can pass
    ``start_number`` argument to the grid to define where to start counting.
    Descendant sorting on ``_numbered`` column decrements the value, you can
    change how numberign function behaves by overloading ``calc_row_no`` 
    property.
    
    
    Converting the grid to a string renders the table rows. That's *just*
    the <tr> tags, not the <table> around them. The part outside the <tr>s
    have too many variations for us to render it. In many template systems,
    you can simply assign the grid to a template variable and it will be
    automatically converted to a string. Example using a Mako template:

    .. code-block:: html

        <table class="stylized">
        <caption>My Lovely Grid</caption>
        <col class="c1" />
        ${my_grid}
        </table>

    The names of the columns will get automatically converted for
    humans ie. foo_bar becomes Foo Bar. If you want the title to be something
    else you can change the grid.labels dict. If you want the column ``part_no``
    to become ``Catalogue Number`` just do::
    
        grid.labels[``part_no``] = u'Catalogue Number'
    
    It may be desired to exclude some or all columns from generation sorting
    urls (used by subclasses that are sorting aware). You can use grids
    exclude_ordering property to pass list of columns that should not support
    sorting. By default sorting is disabled - this ``exclude_ordering`` contains
    every column name.
        
    Since various programmers have different needs, Grid is highly customizable.
    By default grid attempts to read the value from dict directly by key.
    For every column it will try to output value of current_row['colname'].
    
    Since very often this behavior needs to be overridden like we need date
    formatted, use conditionals or generate a link one can use
    the  ``column_formats`` dict and pass a rendering function/lambda to it. 
    For example we want to apppend ``foo`` to part number::
    
        def custem_part_no_td(col_num, i, item):
            return HTML.td(`Foo %s` % item[``part_no``])
        
        grid.column_formats[``part_no``] = custem_part_no_td
    
    You can customize the grids look and behavior by overloading grids instance
    render functions::
    
        grid.default_column_format(self, column_number, i, record, column_name)
        by default generates markup like:
        <td class="cNO">VALUE</td>
        
        grid.default_header_column_format(self, column_number, column_name, 
            header_label)
        by default generates markup like:
        <td class="cNO COLUMN_NAME">VALUE</td>
            
        grid.default_header_ordered_column_format(self, column_number, order, 
            column_name, header_label)
        Used by grids that support ordering of columns in the grid like, 
        webhelpers.pylonslib.grid.GridPylons.
        by default generates markup like:
        <td class="cNO ordering ORDER_DIRECTION COLUMN_NAME">LABEL</td>
        
        grid.default_header_record_format(self, headers)
        by default generates markup like:
        <tr class="header">HEADERS_MARKUP</tr>
        
        grid.default_record_format(self, i, record, columns)
        Make an HTML table from a list of objects, and soon a list of
        sequences, a list of dicts, and a single dict. 
        <tr class="ODD_OR_EVEN">RECORD_MARKUP</tr>
        
        grid.generate_header_link(self, column_number, column, label_text)
        by default just sets the order direction and column properties for grid.
        Actual link generation is handled by sublasses of Grid.
        
        grid.numbered_column_format(self, column_number, i, record)
        by default generates markup like:
        <td class="cNO">RECORD_NO</td>
    """
    def __init__(self, itemlist, columns, column_labels=None,
                  column_formats=None, start_number=1,
                 order_column=None, order_direction=None, request=None,
                 url=None, **kw):
        """ additional keywords are appended to self.additional_kw 
        handy for url generation """
        self.labels = column_labels or {}
        self.exclude_ordering = columns
        self.itemlist = itemlist
        self.columns = columns
        self.column_formats = column_formats or {}
        if "_numbered" in columns:
            self.labels["_numbered"] = "#"
        if "_numbered" not in self.column_formats: 
            self.column_formats["_numbered"] = self.numbered_column_format 
        self.start_number = start_number
        self.order_dir = order_direction
        self.order_column = order_column
        #backward compatibility with old pylons grid
        if not hasattr(self,'request'):
            self.request = request
        self.url_generator = url
        self.additional_kw = kw
    
    def calc_row_no(self, i, column):
        if self.order_dir == 'dsc' and self.order_column == column:
            return self.start_number - i
        else:
            return self.start_number + i
        
    def make_headers(self):
        header_columns = []
            
        for i, column in enumerate(self.columns):
            # let"s generate header column contents
            label_text = ""
            if column in self.labels:
                label_text = self.labels[column]
            else:
                label_text = column.replace("_", " ").title()
            # handle non clickable columns
            if column in self.exclude_ordering:
                header = self.default_header_column_format(i + 1, column,
                    label_text)
            # handle clickable columns
            else:
                header = self.generate_header_link(i + 1, column, label_text)                
            header_columns.append(header)               
        return HTML(*header_columns)
    
    def make_columns(self, i, record):
        columns = []        
        for col_num, column in enumerate(self.columns):
            if column in self.column_formats:
                r = self.column_formats[column](col_num + 1,
                                                self. calc_row_no(i, column),
                                                record)
            else:
                r = self.default_column_format(col_num + 1,
                                               self.calc_row_no(i, column),
                                               record, column)
            columns.append(r)
        return HTML(*columns)
    
    def __html__(self):
        """ renders the grid """
        records = []
        #first render headers record
        headers = self.make_headers()
        r = self.default_header_record_format(headers)
        records.append(r)
        # now lets render the actual item grid
        for i, record in enumerate(self.itemlist):
            columns = self.make_columns(i, record)
            if hasattr(self, 'custom_record_format'):
                r = self.custom_record_format(i + 1, record, columns)
            else:
                r = self.default_record_format(i + 1, record, columns)
            records.append(r)
        return HTML(*records)
    
    def __str__(self):
        return self.__html__()

    def generate_header_link(self, column_number, column, label_text):
        """ This handles generation of link and then decides to call
        ``self.default_header_ordered_column_format`` 
        or 
        ``self.default_header_column_format`` 
        based on whether current column is the one that is used for sorting.
        
        you need to extend Grid class and overload this method implementing
        ordering here, whole operation consists of setting
        self.order_column and self.order_dir to their CURRENT values,
        and generating new urls for state that header should set set after its
        clicked
        
        (additional kw are passed to url gen. - like for webhelpers.paginate)
        example URL generation code below::
        
            GET = dict(self.request.copy().GET) # needs dict() for py2.5 compat
            self.order_column = GET.pop("order_col", None)
            self.order_dir = GET.pop("order_dir", None)       
            # determine new order
            if column == self.order_column and self.order_dir == "asc":
                new_order_dir = "dsc"
            else:
                new_order_dir = "asc"
            self.additional_kw['order_col'] = column
            self.additional_kw['order_dir'] = new_order_dir  
            # generate new url for example url_generator uses 
            # pylons's url.current() or pyramid's current_route_url()
            new_url = self.url_generator(**self.additional_kw)
            # set label for header with link
            label_text = HTML.tag("a", href=new_url, c=label_text)
        """ 
        
        # Is the current column the one we're ordering on?
        if (column == self.order_column):
            return self.default_header_ordered_column_format(column_number,
                                                             column,
                                                             label_text)
        else:
            return self.default_header_column_format(column_number, column,
                                                     label_text)            

    #### Default HTML tag formats ####

    def default_column_format(self, column_number, i, record, column_name):
        class_name = "c%s" % (column_number)
        return HTML.tag("td", record[column_name], class_=class_name)
    
    def numbered_column_format(self, column_number, i, record):
        class_name = "c%s" % (column_number)
        return HTML.tag("td", i, class_=class_name)

    def default_record_format(self, i, record, columns):
        if i % 2 == 0:
            class_name = "even r%s" % i
        else:
            class_name = "odd r%s" % i
        return HTML.tag("tr", columns, class_=class_name)

    def default_header_record_format(self, headers):
        return HTML.tag("tr", headers, class_="header")

    def default_header_ordered_column_format(self, column_number, column_name,
                                             header_label):
        header_label = HTML(header_label, HTML.tag("span", class_="marker"))
        if column_name == "_numbered":
            column_name = "numbered"
        class_name = "c%s ordering %s %s" % (column_number, self.order_dir, column_name)
        return HTML.tag("td", header_label, class_=class_name)

    def default_header_column_format(self, column_number, column_name,
        header_label):
        if column_name == "_numbered":
            column_name = "numbered"
        if column_name in self.exclude_ordering:
            class_name = "c%s %s" % (column_number, column_name)
            return HTML.tag("td", header_label, class_=class_name)
        else:
            header_label = HTML(header_label, HTML.tag("span", class_="marker"))
            class_name = "c%s ordering %s" % (column_number, column_name)
            return HTML.tag("td", header_label, class_=class_name)


class ObjectGrid(Grid):
    """ A grid class for a sequence of objects.
    
    This grid class assumes that the rows are objects rather than dicts, and
    uses attribute access to retrieve the column values. It works well with
    SQLAlchemy ORM instances.
    """
    def default_column_format(self, column_number, i, record, column_name):
        class_name = "c%s" % (column_number)
        return HTML.tag("td", getattr(record, column_name), class_=class_name)

class ListGrid(Grid):
    """ A grid class for a sequence of lists.
    
    This grid class assumes that the rows are lists rather than dicts, and
    uses subscript access to retrieve the column values. Some constructor args
    are also different.

    If ``columns`` is not specified in the constructor, it will examine 
    ``itemlist[0]`` to determine the number of columns, and display them in
    order.  This works only if ``itemlist`` is a sequence and not just an
    iterable.  Alternatively, you can pass an int to specify the number of
    columns, or a list of int subscripts to override the column order.
    Examples::
    
        grid = ListGrid(list_data)
        grid = ListGrid(list_data, columns=4)
        grid = ListGrid(list_data, columns=[1, 3, 2, 0]) 

    ``column_labels`` may be a list of strings. The class will calculate the
    appropriate subscripts for the superclass dict.
    
    """
    def __init__(self, itemlist, columns=None, column_labels=None, *args, **kw):
        if columns is None:
            columns = range(len(itemlist[0]))
        elif isinstance(columns, int):
            columns = range(columns)
        # The superclass requires the ``columns`` elements to be strings.
        super_columns = [str(x) for x in columns]
        # The superclass requires ``column_labels`` to be a dict.
        super_labels = column_labels
        if isinstance(column_labels, (list, tuple)):
            super_labels = dict(zip(super_columns, column_labels))
        Grid.__init__(self, itemlist, super_columns, super_labels, *args, **kw)
  
    def default_column_format(self, column_number, i, record, column_name):
        class_name = "c%s" % (column_number)
        return HTML.tag("td", record[int(column_name)], class_=class_name)
