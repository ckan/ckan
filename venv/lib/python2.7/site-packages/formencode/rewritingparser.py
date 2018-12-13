
import HTMLParser
import re

try:
    from html import escape
except ImportError:  # Python < 3.2
    from cgi import escape

from htmlentitydefs import name2codepoint


def html_quote(v):
    if v is None:
        return ''
    if hasattr(v, '__html__'):
        return v.__html__()
    if isinstance(v, basestring):
        return escape(v, True)
    if hasattr(v, '__unicode__'):
        v = unicode(v)
    else:
        v = str(v)
    return escape(v, True)


class RewritingParser(HTMLParser.HTMLParser):

    listener = None
    skip_next = False

    def __init__(self):
        self._content = []
        HTMLParser.HTMLParser.__init__(self)

    def feed(self, data):
        self.data_is_str = isinstance(data, str)
        self.source = data
        self.lines = data.split('\n')
        self.source_pos = 1, 0
        if self.listener:
            self.listener.reset()
        HTMLParser.HTMLParser.feed(self, data)

    _entityref_re = re.compile('&([a-zA-Z][-.a-zA-Z\d]*);')
    _charref_re = re.compile('&#(\d+|[xX][a-fA-F\d]+);')

    def unescape(self, s):
        s = self._entityref_re.sub(self._sub_entityref, s)
        s = self._charref_re.sub(self._sub_charref, s)
        return s

    def _sub_entityref(self, match):
        name = match.group(1)
        if name not in name2codepoint:
            # If we don't recognize it, pass it through as though it
            # wasn't an entity ref at all
            return match.group(0)
        return unichr(name2codepoint[name])

    def _sub_charref(self, match):
        num = match.group(1)
        if num.lower().startswith('x'):
            num = int(num[1:], 16)
        else:
            num = int(num)
        return unichr(num)

    def handle_misc(self, whatever):
        self.write_pos()
    handle_charref = handle_misc
    handle_entityref = handle_misc
    handle_data = handle_misc
    handle_comment = handle_misc
    handle_decl = handle_misc
    handle_pi = handle_misc
    unknown_decl = handle_misc
    handle_endtag = handle_misc

    def write_tag(self, tag, attrs, startend=False):
        attr_text = ''.join(' %s="%s"' % (n, html_quote(v))
            for (n, v) in attrs if not n.startswith('form:'))
        if startend:
            attr_text += " /"
        self.write_text('<%s%s>' % (tag, attr_text))

    def skip_output(self):
        return False

    def write_pos(self):
        cur_line, cur_offset = self.getpos()
        if self.skip_output():
            self.source_pos = self.getpos()
            return
        if self.skip_next:
            self.skip_next = False
            self.source_pos = self.getpos()
            return
        if cur_line == self.source_pos[0]:
            self.write_text(
                self.lines[cur_line - 1][self.source_pos[1]:cur_offset])
        else:
            self.write_text(
                self.lines[self.source_pos[0] - 1][self.source_pos[1]:])
            self.write_text('\n')
            for i in range(self.source_pos[0] + 1, cur_line):
                self.write_text(self.lines[i - 1])
                self.write_text('\n')
            self.write_text(self.lines[cur_line - 1][:cur_offset])
        self.source_pos = self.getpos()

    def write_text(self, text):
        self._content.append(text)

    def has_attr(self, attr, name):
        for a in attr:
            if a[0].lower() == name:
                return True
        return False

    def get_attr(self, attr, name, default=None):
        for a in attr:
            if a[0].lower() == name:
                return a[1]
        return default

    def set_attr(self, attr, name, value):
        for i, a in enumerate(attr):
            if a[0].lower() == name:
                attr[i] = (name, value)
                return
        attr.append((name, value))

    def del_attr(self, attr, name):
        for i, a in enumerate(attr):
            if a[0].lower() == name:
                del attr[i]
                break

    def add_class(self, attr, class_name):
        current = self.get_attr(attr, 'class', '')
        new = current + ' ' + class_name
        self.set_attr(attr, 'class', new.strip())

    def text(self):
        try:
            return self._text
        except AttributeError:
            raise Exception(
                "You must .close() a parser instance before getting "
                "the text from it")

    def _get_text(self):
        try:
            return ''.join(
                t for t in self._content if not isinstance(t, tuple))
        except UnicodeDecodeError as e:
            if self.data_is_str:
                e.reason += (
                    " the form was passed in as an encoded string, but"
                    " some data or error messages were unicode strings;"
                    " the form should be passed in as a unicode string")
            else:
                e.reason += (
                    " the form was passed in as an unicode string, but"
                    " some data or error message was an encoded string;"
                    " the data and error messages should be passed in as"
                    " unicode strings")
            raise
