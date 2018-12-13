"""
Module to rename form fields
"""

from formencode.rewritingparser import RewritingParser

__all__ = ['rename', 'add_prefix']


def rename(form, rename_func):
    """
    Rename all the form fields in the form (a string), using rename_func

    rename_func will be called with one argument, the name of the
    field, and should return a new name.
    """
    p = RenamingParser(rename_func)
    p.feed(form)
    p.close()
    return p.text()


def add_prefix(form, prefix, dotted=False):
    """
    Add the given prefix to all the fields in the form.

    If dotted is true, then add a dot between prefix and the previous
    name.  Empty fields will use the prefix as the name (with no dot).
    """
    def rename_func(field_name):
        if dotted:
            if field_name:
                return prefix + '.' + field_name
            else:
                return prefix
        else:
            return prefix + field_name
    return rename(form, rename_func)


class RenamingParser(RewritingParser):

    def __init__(self, rename_func):
        RewritingParser.__init__(self)
        self.rename_func = rename_func

    def close(self):
        self.handle_misc(None)
        RewritingParser.close(self)
        self._text = self._get_text()

    def text(self):
        try:
            return self._text
        except AttributeError:
            raise Exception(
                "You must .close() a parser instance before getting "
                "the text from it")

    def handle_starttag(self, tag, attrs, startend=False):
        self.write_pos()
        if tag in ('input', 'textarea', 'select'):
            self.handle_field(tag, attrs, startend)
        else:
            return

    def handle_startendtag(self, tag, attrs):
        return self.handle_starttag(tag, attrs, True)

    def handle_field(self, tag, attrs, startend):
        name = self.get_attr(attrs, 'name', '')
        new_name = self.rename_func(name)
        if name is None:
            self.del_attr(attrs, 'name')
        else:
            self.set_attr(attrs, 'name', new_name)
        self.write_tag(tag, attrs)
        self.skip_next = True
