# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

"""
Formatters for the exception data that comes from ExceptionCollector.
"""
# @@: TODO:
# Use this: http://www.zope.org/Members/tino/VisualTraceback/VisualTracebackNews

import cgi
import re
from paste.util import PySourceColor

def html_quote(s):
    return cgi.escape(str(s), True)

class AbstractFormatter(object):

    general_data_order = ['object', 'source_url']

    def __init__(self, show_hidden_frames=False,
                 include_reusable=True,
                 show_extra_data=True,
                 trim_source_paths=()):
        self.show_hidden_frames = show_hidden_frames
        self.trim_source_paths = trim_source_paths
        self.include_reusable = include_reusable
        self.show_extra_data = show_extra_data

    def format_collected_data(self, exc_data):
        general_data = {}
        if self.show_extra_data:
            for name, value_list in exc_data.extra_data.items():
                if isinstance(name, tuple):
                    importance, title = name
                else:
                    importance, title = 'normal', name
                for value in value_list:
                    general_data[(importance, name)] = self.format_extra_data(
                        importance, title, value)
        lines = []
        frames = self.filter_frames(exc_data.frames)
        for frame in frames:
            sup = frame.supplement
            if sup:
                if sup.object:
                    general_data[('important', 'object')] = self.format_sup_object(
                        sup.object)
                if sup.source_url:
                    general_data[('important', 'source_url')] = self.format_sup_url(
                        sup.source_url)
                if sup.line:
                    lines.append(self.format_sup_line_pos(sup.line, sup.column))
                if sup.expression:
                    lines.append(self.format_sup_expression(sup.expression))
                if sup.warnings:
                    for warning in sup.warnings:
                        lines.append(self.format_sup_warning(warning))
                if sup.info:
                    lines.extend(self.format_sup_info(sup.info))
            if frame.supplement_exception:
                lines.append('Exception in supplement:')
                lines.append(self.quote_long(frame.supplement_exception))
            if frame.traceback_info:
                lines.append(self.format_traceback_info(frame.traceback_info))
            filename = frame.filename
            if filename and self.trim_source_paths:
                for path, repl in self.trim_source_paths:
                    if filename.startswith(path):
                        filename = repl + filename[len(path):]
                        break
            lines.append(self.format_source_line(filename or '?', frame))
            source = frame.get_source_line()
            long_source = frame.get_source_line(2)
            if source:
                lines.append(self.format_long_source(
                    source, long_source))
        etype = exc_data.exception_type
        if not isinstance(etype, basestring):
            etype = etype.__name__
        exc_info = self.format_exception_info(
            etype,
            exc_data.exception_value)
        data_by_importance = {'important': [], 'normal': [],
                              'supplemental': [], 'extra': []}
        for (importance, name), value in general_data.items():
            data_by_importance[importance].append(
                (name, value))
        for value in data_by_importance.values():
            value.sort()
        return self.format_combine(data_by_importance, lines, exc_info)

    def filter_frames(self, frames):
        """
        Removes any frames that should be hidden, according to the
        values of traceback_hide, self.show_hidden_frames, and the
        hidden status of the final frame.
        """
        if self.show_hidden_frames:
            return frames
        new_frames = []
        hidden = False
        for frame in frames:
            hide = frame.traceback_hide
            # @@: It would be nice to signal a warning if an unknown
            # hide string was used, but I'm not sure where to put
            # that warning.
            if hide == 'before':
                new_frames = []
                hidden = False
            elif hide == 'before_and_this':
                new_frames = []
                hidden = False
                continue
            elif hide == 'reset':
                hidden = False
            elif hide == 'reset_and_this':
                hidden = False
                continue
            elif hide == 'after':
                hidden = True
            elif hide == 'after_and_this':
                hidden = True
                continue
            elif hide:
                continue
            elif hidden:
                continue
            new_frames.append(frame)
        if frames[-1] not in new_frames:
            # We must include the last frame; that we don't indicates
            # that the error happened where something was "hidden",
            # so we just have to show everything
            return frames
        return new_frames

    def pretty_string_repr(self, s):
        """
        Formats the string as a triple-quoted string when it contains
        newlines.
        """
        if '\n' in s:
            s = repr(s)
            s = s[0]*3 + s[1:-1] + s[-1]*3
            s = s.replace('\\n', '\n')
            return s
        else:
            return repr(s)

    def long_item_list(self, lst):
        """
        Returns true if the list contains items that are long, and should
        be more nicely formatted.
        """
        how_many = 0
        for item in lst:
            if len(repr(item)) > 40:
                how_many += 1
                if how_many >= 3:
                    return True
        return False

class TextFormatter(AbstractFormatter):

    def quote(self, s):
        return s
    def quote_long(self, s):
        return s
    def emphasize(self, s):
        return s
    def format_sup_object(self, obj):
        return 'In object: %s' % self.emphasize(self.quote(repr(obj)))
    def format_sup_url(self, url):
        return 'URL: %s' % self.quote(url)
    def format_sup_line_pos(self, line, column):
        if column:
            return self.emphasize('Line %i, Column %i' % (line, column))
        else:
            return self.emphasize('Line %i' % line)
    def format_sup_expression(self, expr):
        return self.emphasize('In expression: %s' % self.quote(expr))
    def format_sup_warning(self, warning):
        return 'Warning: %s' % self.quote(warning)
    def format_sup_info(self, info):
        return [self.quote_long(info)]
    def format_source_line(self, filename, frame):
        return 'File %r, line %s in %s' % (
            filename, frame.lineno or '?', frame.name or '?')
    def format_long_source(self, source, long_source):
        return self.format_source(source)
    def format_source(self, source_line):
        return '  ' + self.quote(source_line.strip())
    def format_exception_info(self, etype, evalue):
        return self.emphasize(
            '%s: %s' % (self.quote(etype), self.quote(evalue)))
    def format_traceback_info(self, info):
        return info
        
    def format_combine(self, data_by_importance, lines, exc_info):
        lines[:0] = [value for n, value in data_by_importance['important']]
        lines.append(exc_info)
        for name in 'normal', 'supplemental', 'extra':
            lines.extend([value for n, value in data_by_importance[name]])
        return self.format_combine_lines(lines)

    def format_combine_lines(self, lines):
        return '\n'.join(lines)

    def format_extra_data(self, importance, title, value):
        if isinstance(value, str):
            s = self.pretty_string_repr(value)
            if '\n' in s:
                return '%s:\n%s' % (title, s)
            else:
                return '%s: %s' % (title, s)
        elif isinstance(value, dict):
            lines = ['\n', title, '-'*len(title)]
            items = value.items()
            items.sort()
            for n, v in items:
                try:
                    v = repr(v)
                except Exception, e:
                    v = 'Cannot display: %s' % e
                v = truncate(v)
                lines.append('  %s: %s' % (n, v))
            return '\n'.join(lines)
        elif (isinstance(value, (list, tuple))
              and self.long_item_list(value)):
            parts = [truncate(repr(v)) for v in value]
            return '%s: [\n    %s]' % (
                title, ',\n    '.join(parts))
        else:
            return '%s: %s' % (title, truncate(repr(value)))

class HTMLFormatter(TextFormatter):

    def quote(self, s):
        return html_quote(s)
    def quote_long(self, s):
        return '<pre>%s</pre>' % self.quote(s)
    def emphasize(self, s):
        return '<b>%s</b>' % s
    def format_sup_url(self, url):
        return 'URL: <a href="%s">%s</a>' % (url, url)
    def format_combine_lines(self, lines):
        return '<br>\n'.join(lines)
    def format_source_line(self, filename, frame):
        name = self.quote(frame.name or '?')
        return 'Module <span class="module" title="%s">%s</span>:<b>%s</b> in <code>%s</code>' % (
            filename, frame.modname or '?', frame.lineno or '?',
            name)
        return 'File %r, line %s in <tt>%s</tt>' % (
            filename, frame.lineno, name)
    def format_long_source(self, source, long_source):
        q_long_source = str2html(long_source, False, 4, True)
        q_source = str2html(source, True, 0, False)
        return ('<code style="display: none" class="source" source-type="long"><a class="switch_source" onclick="return switch_source(this, \'long\')" href="#">&lt;&lt;&nbsp; </a>%s</code>'
                '<code class="source" source-type="short"><a onclick="return switch_source(this, \'short\')" class="switch_source" href="#">&gt;&gt;&nbsp; </a>%s</code>'
                % (q_long_source,
                   q_source))
    def format_source(self, source_line):
        return '&nbsp;&nbsp;<code class="source">%s</code>' % self.quote(source_line.strip())
    def format_traceback_info(self, info):
        return '<pre>%s</pre>' % self.quote(info)

    def format_extra_data(self, importance, title, value):
        if isinstance(value, str):
            s = self.pretty_string_repr(value)
            if '\n' in s:
                return '%s:<br><pre>%s</pre>' % (title, self.quote(s))
            else:
                return '%s: <tt>%s</tt>' % (title, self.quote(s))
        elif isinstance(value, dict):
            return self.zebra_table(title, value)
        elif (isinstance(value, (list, tuple))
              and self.long_item_list(value)):
            return '%s: <tt>[<br>\n&nbsp; &nbsp; %s]</tt>' % (
                title, ',<br>&nbsp; &nbsp; '.join(map(self.quote, map(repr, value))))
        else:
            return '%s: <tt>%s</tt>' % (title, self.quote(repr(value)))

    def format_combine(self, data_by_importance, lines, exc_info):
        lines[:0] = [value for n, value in data_by_importance['important']]
        lines.append(exc_info)
        for name in 'normal', 'supplemental':
            lines.extend([value for n, value in data_by_importance[name]])
        if data_by_importance['extra']:
            lines.append(
                '<script type="text/javascript">\nshow_button(\'extra_data\', \'extra data\');\n</script>\n' +
                '<div id="extra_data" class="hidden-data">\n')
            lines.extend([value for n, value in data_by_importance['extra']])
            lines.append('</div>')
        text = self.format_combine_lines(lines)
        if self.include_reusable:
            return error_css + hide_display_js + text
        else:
            # Usually because another error is already on this page,
            # and so the js & CSS are unneeded
            return text

    def zebra_table(self, title, rows, table_class="variables"):
        if isinstance(rows, dict):
            rows = rows.items()
            rows.sort()
        table = ['<table class="%s">' % table_class,
                 '<tr class="header"><th colspan="2">%s</th></tr>'
                 % self.quote(title)]
        odd = False
        for name, value in rows:
            try:
                value = repr(value)
            except Exception, e:
                value = 'Cannot print: %s' % e
            odd = not odd
            table.append(
                '<tr class="%s"><td>%s</td>'
                % (odd and 'odd' or 'even', self.quote(name)))
            table.append(
                '<td><tt>%s</tt></td></tr>'
                % make_wrappable(self.quote(truncate(value))))
        table.append('</table>')
        return '\n'.join(table)

hide_display_js = r'''
<script type="text/javascript">
function hide_display(id) {
    var el = document.getElementById(id);
    if (el.className == "hidden-data") {
        el.className = "";
        return true;
    } else {
        el.className = "hidden-data";
        return false;
    }
}
document.write('<style type="text/css">\n');
document.write('.hidden-data {display: none}\n');
document.write('</style>\n');
function show_button(toggle_id, name) {
    document.write('<a href="#' + toggle_id
        + '" onclick="javascript:hide_display(\'' + toggle_id
        + '\')" class="button">' + name + '</a><br>');
}

function switch_source(el, hide_type) {
    while (el) {
        if (el.getAttribute &&
            el.getAttribute('source-type') == hide_type) {
            break;
        }
        el = el.parentNode;
    }
    if (! el) {
        return false;
    }
    el.style.display = 'none';
    if (hide_type == 'long') {
        while (el) {
            if (el.getAttribute &&
                el.getAttribute('source-type') == 'short') {
                break;
            }
            el = el.nextSibling;
        }
    } else {
        while (el) {
            if (el.getAttribute &&
                el.getAttribute('source-type') == 'long') {
                break;
            }
            el = el.previousSibling;
        }
    }
    if (el) {
        el.style.display = '';
    }
    return false;
}

</script>'''
    

error_css = """
<style type="text/css">
body {
  font-family: Helvetica, sans-serif;
}

table {
  width: 100%;
}

tr.header {
  background-color: #006;
  color: #fff;
}

tr.even {
  background-color: #ddd;
}

table.variables td {
  vertical-align: top;
  overflow: auto;
}

a.button {
  background-color: #ccc;
  border: 2px outset #aaa;
  color: #000;
  text-decoration: none;
}

a.button:hover {
  background-color: #ddd;
}

code.source {
  color: #006;
}

a.switch_source {
  color: #090;
  text-decoration: none;
}

a.switch_source:hover {
  background-color: #ddd;
}

.source-highlight {
  background-color: #ff9;
}

</style>
"""

def format_html(exc_data, include_hidden_frames=False, **ops):
    if not include_hidden_frames:
        return HTMLFormatter(**ops).format_collected_data(exc_data)
    short_er = format_html(exc_data, show_hidden_frames=False, **ops)
    # @@: This should have a way of seeing if the previous traceback
    # was actually trimmed at all
    ops['include_reusable'] = False
    ops['show_extra_data'] = False
    long_er = format_html(exc_data, show_hidden_frames=True, **ops)
    text_er = format_text(exc_data, show_hidden_frames=True, **ops)
    return """
    %s
    <br>
    <script type="text/javascript">
    show_button('full_traceback', 'full traceback')
    </script>
    <div id="full_traceback" class="hidden-data">
    %s
    </div>
    <br>
    <script type="text/javascript">
    show_button('text_version', 'text version')
    </script>
    <div id="text_version" class="hidden-data">
    <textarea style="width: 100%%" rows=10 cols=60>%s</textarea>
    </div>
    """ % (short_er, long_er, cgi.escape(text_er))
        
def format_text(exc_data, **ops):
    return TextFormatter(**ops).format_collected_data(exc_data)

whitespace_re = re.compile(r'  +')
pre_re = re.compile(r'</?pre.*?>')
error_re = re.compile(r'<h3>ERROR: .*?</h3>')

def str2html(src, strip=False, indent_subsequent=0,
             highlight_inner=False):
    """
    Convert a string to HTML.  Try to be really safe about it,
    returning a quoted version of the string if nothing else works.
    """
    try:
        return _str2html(src, strip=strip,
                         indent_subsequent=indent_subsequent,
                         highlight_inner=highlight_inner)
    except:
        return html_quote(src)

def _str2html(src, strip=False, indent_subsequent=0,
              highlight_inner=False):
    if strip:
        src = src.strip()
    orig_src = src
    try:
        src = PySourceColor.str2html(src, form='snip')
        src = error_re.sub('', src)
        src = pre_re.sub('', src)
        src = re.sub(r'^[\n\r]{0,1}', '', src)
        src = re.sub(r'[\n\r]{0,1}$', '', src)
    except:
        src = html_quote(orig_src)
    lines = src.splitlines()
    if len(lines) == 1:
        return lines[0]
    indent = ' '*indent_subsequent
    for i in range(1, len(lines)):
        lines[i] = indent+lines[i]
        if highlight_inner and i == len(lines)/2:
            lines[i] = '<span class="source-highlight">%s</span>' % lines[i]
    src = '<br>\n'.join(lines)
    src = whitespace_re.sub(
        lambda m: '&nbsp;'*(len(m.group(0))-1) + ' ', src)
    return src

def truncate(string, limit=1000):
    """
    Truncate the string to the limit number of
    characters
    """
    if len(string) > limit:
        return string[:limit-20]+'...'+string[-17:]
    else:
        return string

def make_wrappable(html, wrap_limit=60,
                   split_on=';?&@!$#-/\\"\''):
    # Currently using <wbr>, maybe should use &#8203;
    #   http://www.cs.tut.fi/~jkorpela/html/nobr.html
    if len(html) <= wrap_limit:
        return html
    words = html.split()
    new_words = []
    for word in words:
        wrapped_word = ''
        while len(word) > wrap_limit:
            for char in split_on:
                if char in word:
                    first, rest = word.split(char, 1)
                    wrapped_word += first+char+'<wbr>'
                    word = rest
                    break
            else:
                for i in range(0, len(word), wrap_limit):
                    wrapped_word += word[i:i+wrap_limit]+'<wbr>'
                word = ''
        wrapped_word += word
        new_words.append(wrapped_word)
    return ' '.join(new_words)

def make_pre_wrappable(html, wrap_limit=60,
                       split_on=';?&@!$#-/\\"\''):
    """
    Like ``make_wrappable()`` but intended for text that will
    go in a ``<pre>`` block, so wrap on a line-by-line basis.
    """
    lines = html.splitlines()
    new_lines = []
    for line in lines:
        if len(line) > wrap_limit:
            for char in split_on:
                if char in line:
                    parts = line.split(char)
                    line = '<wbr>'.join(parts)
                    break
        new_lines.append(line)
    return '\n'.join(lines)
