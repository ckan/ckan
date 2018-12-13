# This is a private implementation module.  Import render() and sanitize()
# from webhelpers.html.converters .

# Contributed by Ian Bicking, downloaded from
# http://svn.w4py.org/ZPTKit/trunk/ZPTKit/htmlrender.py
# (Webware for Python framework)
#
# Changed by Mike Orr:
# - Add ``render()`` docstring.  Export only that function by default.
# - Add ``sanitize()`` and ``HTMLSanitizer.
# - Change code when run as a script.
# - Don't convert Unicode to text.
# - Drop textwrap backport.  (WebHelpers doesn't support Python < 2.3.)


##########################################################################
#
# Copyright (c) 2005 Imaginary Landscape LLC and Contributors.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
##########################################################################
"""An HTML-to-text formatter and HTML sanitizer.
"""

from HTMLParser import HTMLParser
import htmlentitydefs
import re
import textwrap

__all__ = ["render", "sanitize"]

#### Public
def render(html, width=70):
    """Render HTML as formatted text, like lynx's "print" function.

    Paragraphs are collected and wrapped at the specified width, default 70.
    Blockquotes are indented.  Paragraphs cannot be nested at this time.  HTML
    entities are substituted.  
    
    The formatting is simplistic, and works best with HTML that was written
    for this renderer (e.g., ZPTKit.emailtemplate).

    The output usually ends with two newlines.  If the input ends with a close
    tag plus any whitespace, the output ends with four newlines.  This is
    probably a bug.
    """
    context = Context()
    context.width = width
    context.indent = 0
    p = HTMLRenderer()
    p.feed(html)
    p.close()
    paras = [para.to_text(context)
             for para in p.paragraphs
             if para]
    return "".join(paras)

def sanitize(html):
    """Strip all HTML tags but leave their content.

    Use this to strip any potentially malicious tags from user input.

    HTML entities are left as-is.

    Usage::

        >>> sanitize(u'I <i>really</i> like steak!')
        u'I really like steak!'
        >>> sanitize(u'I <i>really</i> like <script language="javascript">NEFARIOUS CODE</script> steak!')
        u'I really like NEFARIOUS CODE steak!'
    """
    p = HTMLSanitizer()
    p.feed(html)
    p.close()
    return "".join(p.output_chunks)

#### Private (though safe to use)
class HTMLRenderer(HTMLParser):

    block_tags = 'p div blockquote h1 h2 h3 h4 h5 h6 ul ol'.split()

    def reset(self):
        HTMLParser.reset(self)
        self.paragraphs = []
        self.in_paragraph = None
        self.last_href = None
        self.href_content = None
        self.in_table = None
        self.cell_content = None
        self.list_type = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == 'body':
            self.paragraphs = []
            self.in_paragraph = None
        if tag == 'blockquote':
            self.paragraphs.append(Indenter(4))
        if tag in self.block_tags:
            self.start_para(tag, attrs)
        if tag == 'br':
            self.add_br(tag, attrs)
        if tag == 'a':
            self.last_href = self.get_attr(attrs, 'href')
            self.href_content = []
        if tag == 'img':
            alt = self.get_attr(attrs, 'alt')
            if alt:
                self.handle_data(alt)
        if tag == 'table':
            # @@: This is a hacky way of dealing with nested
            # tables.  Basically the tables are crudely flattened,
            # and we keep track of how many <table>'s we see based
            # on the table.depth attribute (so we can later remove
            # the table when sufficient </table>'s have been seen)
            if self.in_table:
                self.in_table.depth += 1
            else:
                self.in_table = Table()
        if tag == 'tr':
            self.in_table.add_row()
        if tag == 'td':
            self.cell_content = []
        if tag == 'ul':
            self.paragraphs.append(Indenter(2))
            self.list_type.append('ul')
        if tag == 'ol':
            self.paragraphs.append(Indenter(2))
            self.list_type.append(1)
        if tag == 'li':
            self.add_br(None, None)
            if not self.list_type or self.list_type[-1] == 'ul':
                self.handle_data('* ')
            else:
                self.handle_data('%i) ' % self.list_type[-1])
                self.list_type[-1] += 1

    def handle_endtag(self, tag):
        if tag in self.block_tags:
            self.end_para(tag)
        if tag == 'a':
            if self.href_content:
                content = ''.join(self.href_content)
            else:
                content = None
            self.href_content = None
            if content and self.last_href and content != self.last_href:
                self.handle_data(' <%s>' % self.last_href)
            self.last_href = None
        if tag == 'table':
            self.paragraphs.append(self.in_table)
            self.in_table.depth -= 1
            if not self.in_table.depth:
                self.in_table = None
        if tag == 'td':
            self.end_para(tag)
            if self.paragraphs:
                self.in_table.add_cell(self.paragraphs[-1])
                self.paragraphs.pop()
        if tag == 'ul' or tag == 'ol':
            self.paragraphs.append(Indenter(-2))
            self.list_type.pop()
        if tag == 'blockquote':
            self.paragraphs.append(Indenter(-4))

    def handle_data(self, data):
        if self.in_paragraph is None:
            self.start_para(None, None)
        self.in_paragraph.add_text(data)
        if self.href_content is not None:
            self.href_content.append(data)

    def handle_entityref(self, name):
        name = name.lower()
        if name not in htmlentitydefs.entitydefs:
            # bad entity, just let it through
            # (like a &var=value in a URL)
            self.handle_data('&'+name)
            return
        result = htmlentitydefs.entitydefs[name]
        if result.startswith('&'):
            self.handle_charref(result[2:-1])
        else:
            self.handle_data(result)

    def handle_charref(self, name):
        try:
            self.handle_data(unichr(int(name)))
        except ValueError:
            self.handle_data('&' + name)
        
    def start_para(self, tag, attrs):
        if tag is None:
            # Implicit paragraph
            tag = 'p'
            attrs = []
        self.end_para(None)
        self.in_paragraph = Paragraph(tag, attrs)

    def end_para(self, tag):
        if self.in_paragraph:
            self.paragraphs.append(self.in_paragraph)
        self.in_paragraph = None

    def add_br(self, tag, attrs):
        if not self.in_paragraph:
            self.start_para(None, None)
        self.in_paragraph.add_tag('<br>')

    def close(self):
        HTMLParser.close(self)
        self.end_para(None)

    def get_attr(self, attrs, name, default=None):
        for attr_name, value in attrs:
            if attr_name.lower() == name.lower():
                return value
        return default
    
class Paragraph:

    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
        self.text = []
        self._default_align = 'left'

    def __repr__(self):
        length = len(''.join(map(str, self.text)))
        attrs = ' '.join([self.tag] +
                         ['%s="%s"' % (name, value)
                          for name, value in self.attrs] +
                         ['length=%i' % length])
        return '<Paragraph %s: %s>' % (hex(id(self))[2:], attrs)
        
    def add_text(self, text):
        self.text.append(text)

    def add_tag(self, tag):
        self.text.append([tag])

    def to_text(self, context):
        lines = self.make_lines()
        width = context.width
        indent = context.indent
        wrapped_lines = []
        for line in lines:
            wrapped = textwrap.wrap(
                line,
                width,
                replace_whitespace=True,
                initial_indent=' '*indent,
                subsequent_indent=' '*indent,
                fix_sentence_endings=False,
                break_long_words=False)
            wrapped_lines.extend(wrapped)
        if self.tag in ('h1', 'h2'):
            self._default_align = 'center'
        lines = self.align_lines(wrapped_lines, width)
        text = '\n'.join(lines)
        if self.tag in ('h1', 'h3'):
            text = text.upper()
        if self.tag == 'h4':
            text = '*%s*' % text
        return text + '\n\n'

    def align_lines(self, lines, width):
        if self.alignment() == 'right':
            return [' '*(width-len(line))+line
                     for line in lines]
        elif self.alignment() == 'center':
            return [' '*((width-len(line))/2)+line
                    for line in lines]
        elif self.alignment() == 'left':
            return lines
        else:
            # Could be odd things like 'baseline'; treat it as normal
            return lines

    def make_lines(self):
        lines = ['']
        for data in self.text:
            if isinstance(data, list):
                tag = data[0]
                if tag == '<br>':
                    lines.append('')
                else:
                    assert 0, "Unknown tag: %r" % tag
            else:
                lines[-1] = lines[-1] + data
        return [normalize(line).strip()
                for line in lines
                if line]

    def alignment(self):
        for name, value in self.attrs:
            if name.lower() == 'align':
                return value.lower()
        return self._default_align

    def __nonzero__(self):
        for t in self.text:
            if t:
                return True
        return False

class Table:

    def __init__(self):
        self.rows = []
        self.row_num = 0
        self.depth = 1

    def add_row(self):
        self.row_num += 1
        self.rows.append([])

    def add_cell(self, value):
        self.rows[-1].append(value)

    def __nonzero__(self):
        return not not self.rows

    def to_text(self, context):
        if self.rows and not self.rows[-1]:
            # Get rid of blank last line
            self.rows.pop()
        if not self.rows:
            return ''
        headers = [p.to_text(context).strip() for p in self.rows.pop(0)]
        context.indent += 4
        lines = []
        for row in self.rows:
            for header, cell in zip(headers, row):
                cell_text = cell.to_text(context).strip()
                lines.append('%s: %s' % (header, cell_text))
            lines.append('')
        context.indent -= 4
        return '\n'.join(lines) + '\n\n'

class Indenter:

    def __init__(self, indent):
        self.indent = indent

    def to_text(self, context):
        context.indent += self.indent
        return ''

class Context:
    pass

class HTMLSanitizer(HTMLParser):

    def reset(self):
        HTMLParser.reset(self)
        self.output_chunks = []

    def handle_data(self, data):
        self.output_chunks.append(data)


def normalize(text):
    text = re.sub(r'\s+', ' ', text)
    # nbsp:
    if not isinstance(text, unicode):
        text = text.replace('\xa0', ' ')
    return text

#### Main routine
def main():
    import os
    import sys
    if len(sys.argv) > 1:
        prog = os.path.basename(sys.argv[0])
        sys.exit("usage: %s <HTML_FILE" % prog)
    html = sys.stdin.read()
    print render(html)

if __name__ == "__main__":  main()
