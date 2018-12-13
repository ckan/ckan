# coding: utf-8
"""Functions that output text (not HTML).

Helpers for filtering, formatting, and transforming strings.
"""

import re
import textwrap
import urllib

from webhelpers.html.tools import strip_tags

try:
    from unidecode import unidecode
except ImportError:
    unidecode = None

__all__ = [
    "chop_at",
    "collapse",
    "convert_accented_entities",
    #"convert_misc_characters",   # DISABLED
    "convert_misc_entities",
    "excerpt",
    "lchop",
    "plural",
    "rchop",
    "remove_formatting",
    "replace_whitespace",
    "series",
    "strip_leading_whitespace",
    "truncate", 
    "urlify",
    "wrap_paragraphs",
    ]

def truncate(text, length=30, indicator='...', whole_word=False):
    """Truncate ``text`` with replacement characters.
    
    ``length``
        The maximum length of ``text`` before replacement
    ``indicator``
        If ``text`` exceeds the ``length``, this string will replace
        the end of the string
    ``whole_word``
        If true, shorten the string further to avoid breaking a word in the
        middle.  A word is defined as any string not containing whitespace.
        If the entire text before the break is a single word, it will have to
        be broken.

    Example::

        >>> truncate('Once upon a time in a world far far away', 14)
        'Once upon a...'
        
    """
    if not text: 
        return ""
    if len(text) <= length:
        return text
    short_length = length - len(indicator)
    if not whole_word:
        return text[:short_length] + indicator
    # Go back to end of previous word.
    i = short_length
    while i >= 0 and not text[i].isspace():
        i -= 1
    while i >= 0 and text[i].isspace():
        i -= 1
    #if i < short_length:
    #    i += 1   # Set to one after the last char we want to keep.
    if i <= 0:
        # Entire text before break is one word, or we miscalculated.
        return text[:short_length] + indicator
    return text[:i+1] + indicator


def excerpt(text, phrase, radius=100, excerpt_string="..."):
    """Extract an excerpt from the ``text``, or '' if the phrase isn't
    found.

    ``phrase``
        Phrase to excerpt from ``text``
    ``radius``
        How many surrounding characters to include
    ``excerpt_string``
        Characters surrounding entire excerpt
    
    Example::
    
        >>> excerpt("hello my world", "my", 3)
        '...lo my wo...'

    """
    if not text or not phrase:
        return text

    pat = re.compile('(.{0,%s}%s.{0,%s})' % (radius, re.escape(phrase), 
                                             radius), re.I)
    match = pat.search(text)
    if not match:
        return ""
    excerpt = match.expand(r'\1')
    if match.start(1) > 0:
        excerpt = excerpt_string + excerpt
    if match.end(1) < len(text):
        excerpt = excerpt + excerpt_string
    if hasattr(text, '__html__'):
        return literal(excertp)
    else:
        return excerpt


def plural(n, singular, plural, with_number=True):
    """Return the singular or plural form of a word, according to the number.

    If ``with_number`` is true (default), the return value will be the number
    followed by the word. Otherwise the word alone will be returned.

    Usage:

    >>> plural(2, "ox", "oxen")
    '2 oxen'
    >>> plural(2, "ox", "oxen", False)
    'oxen'
    """
    if n == 1:
        form = singular
    else:
        form = plural
    if with_number:
        return "%s %s" % (n, form)
    else:
        return form

def chop_at(s, sub, inclusive=False):
    """Truncate string ``s`` at the first occurrence of ``sub``.

    If ``inclusive`` is true, truncate just after ``sub`` rather than at it.

    >>> chop_at("plutocratic brats", "rat")
    'plutoc'
    >>> chop_at("plutocratic brats", "rat", True)
    'plutocrat'
    """
    pos = s.find(sub)
    if pos == -1:
        return s
    if inclusive:
        return s[:pos+len(sub)]
    return s[:pos]

def lchop(s, sub):
    """Chop ``sub`` off the front of ``s`` if present.

    >>> lchop("##This is a comment.##", "##")
    'This is a comment.##'

    The difference between ``lchop`` and ``s.lstrip`` is that ``lchop`` strips
    only the exact prefix, while ``s.lstrip`` treats the argument as a set of
    leading characters to delete regardless of order.
    """
    if s.startswith(sub):
        s = s[len(sub):]
    return s
    
def rchop(s, sub):
    """Chop ``sub`` off the end of ``s`` if present.
    
    >>> rchop("##This is a comment.##", "##")
    '##This is a comment.'

    The difference between ``rchop`` and ``s.rstrip`` is that ``rchop`` strips
    only the exact suffix, while ``s.rstrip`` treats the argument as a set of
    trailing characters to delete regardless of order.
    """
    if s.endswith(sub):
        s = s[:-len(sub)]
    return s

def strip_leading_whitespace(s):
    """Strip the leading whitespace in all lines in ``s``.
    
    This deletes *all* leading whitespace.  ``textwrap.dedent`` deletes only
    the whitespace common to all lines.
    """
    ret = [x.lstrip() for x in s.splitlines(True)]
    return "".join(ret)

def wrap_paragraphs(text, width=72):
    """Wrap all paragraphs in a text string to the specified width.

    ``width`` may be an int or a ``textwrap.TextWrapper`` instance.  
    The latter allows you to set other options besides the width, and is more
    efficient when wrapping many texts.  
    """
    if isinstance(width, textwrap.TextWrapper):
        wrapper = width
    else:
        wrapper = textwrap.TextWrapper(width=width)
    result = []
    lines = text.splitlines(True)
    lines_len = len(lines)
    start = 0
    end = None
    while start < lines_len:
        # Leave short lines as-is.
        if len(lines[start]) <= width:
            result.append(lines[start])
            start += 1
            continue
        # Found a long line, peek forward to end of paragraph.
        end = start + 1
        while end < lines_len and not lines[end].isspace():
            end += 1
        # 'end' is one higher than last long lone.
        paragraph = ''.join(lines[start:end])
        paragraph = wrapper.fill(paragraph) + "\n"
        result.append(paragraph)
        start = end
        end = None
    return "".join(result)

def series(items, conjunction="and", strict_commas=True):
    """Join strings using commas and a conjunction such as "and" or "or".

    Examples:

    >>> series(["A", "B", "C"])
    'A, B, and C'
    >>> series(["A", "B", "C"], "or")
    'A, B, or C'
    >>> series(["A", "B", "C"], strict_commas=False)
    'A, B and C'
    >>> series(["A", "B"])
    'A and B'
    >>> series(["A"])
    'A'
    >>> series([])
    ''
    """
    items = list(items)
    length = len(items)
    if length == 0:
        return ""
    if length == 1:
        return items[0]
    if length == 2:
        strict_commas = False
    nonlast = ", ".join(items[:-1])
    last = items[-1]
    comma = strict_commas and "," or ""
    return "%s%s %s %s" % (nonlast, comma, conjunction, last)

def urlify(string):
    """Create a URI-friendly representation of the string
    
    Can be called manually in order to generate an URI-friendly version
    of any string.

    If the ``unidecode`` package is installed, it will also transliterate 
    non-ASCII Unicode characters to their nearest pronounciation equivalent in
    ASCII.

    Examples::
        >>> urlify("Mighty Mighty Bosstones")
        'mighty-mighty-bosstones'

    Based on Ruby's stringex package
    (http://github.com/rsl/stringex/tree/master)

    Changed in WebHelpers 1.2: urlecode the result in case it contains special
    characters like "?". 
    """
    s = remove_formatting(string).lower()
    s = replace_whitespace(s, '-')
    s = collapse(s, '-')
    return urllib.quote(s)


def remove_formatting(string):
    """Simplify HTML text by removing tags and several kinds of formatting.
    
    If the ``unidecode`` package is installed, it will also transliterate 
    non-ASCII Unicode characters to their nearest pronunciation equivalent in
    ASCII.

    Based on Ruby's stringex package
    (http://github.com/rsl/stringex/tree/master)
    """
    s = strip_tags(string)
    s = convert_accented_entities(s)
    s = convert_misc_entities(s)
    #s = convert_misc_characters(s)
    if unidecode:
        s = unidecode(s)
    return collapse(s)


def convert_accented_entities(string):
    """Converts HTML entities into the respective non-accented letters.
    
    Examples::
    
      >>> convert_accented_entities("&aacute;")
      'a'
      >>> convert_accented_entities("&ccedil;")
      'c'
      >>> convert_accented_entities("&egrave;")
      'e'
      >>> convert_accented_entities("&icirc;")
      'i'
      >>> convert_accented_entities("&oslash;")
      'o'
      >>> convert_accented_entities("&uuml;")
      'u'
    
    Note: This does not do any conversion of Unicode/ASCII
    accented-characters. For that functionality please use unidecode.
    
    Based on Ruby's stringex package
    (http://github.com/rsl/stringex/tree/master)
    """
    return re.sub(r'\&([A-Za-z])(grave|acute|circ|tilde|uml|ring|cedil|slash);',
                  r'\1', string)


def convert_misc_entities(string):
    """Converts HTML entities (taken from common Textile formattings) 
    into plain text formats
    
    Note: This isn't an attempt at complete conversion of HTML
    entities, just those most likely to be generated by Textile.
    
    Based on Ruby's stringex package
    (http://github.com/rsl/stringex/tree/master)
    """
    replace_dict = {
        "#822[01]": "\"",
        "#821[67]": "'",
        "#8230": "...",
        "#8211": "-",
        "#8212": "--",
        "#215": "x",
        "gt": ">",
        "lt": "<",
        "(#8482|trade)": "(tm)",
        "(#174|reg)": "(r)",
        "(#169|copy)": "(c)",
        "(#38|amp)": "and",
        "nbsp": " ",
        "(#162|cent)": " cent",
        "(#163|pound)": " pound",
        "(#188|frac14)": "one fourth",
        "(#189|frac12)": "half",
        "(#190|frac34)": "three fourths",
        "(#176|deg)": " degrees"
    }
    for textiled, normal in replace_dict.items():
        string = re.sub(r'\&%s;' % textiled, normal, string)
    return re.sub(r'\&[^;]+;', '', string)


'''*** DISABLED convert_misc_characters: fails doc tests.
Confirming what behavior should be.

def convert_misc_characters(string):
    """Converts various common plaintext characters to a more
    URI-friendly representation
    
    Examples::
      
        >>> convert_misc_characters("foo & bar")
        'foo and bar'
        >>> convert_misc_characters("Chanel #9")
        'Chanel number nine'
        >>> convert_misc_characters("user@host")
        'user at host'
        >>> convert_misc_characters("google.com")
        'google dot com'
        >>> convert_misc_characters("$10")
        '10 dollars'
        >>> convert_misc_characters("*69")
        'star 69'
        >>> convert_misc_characters("100%")
        '100 percent'
        >>> convert_misc_characters("windows/mac/linux")
        'windows slash mac slash linux'
      
    Note: Because this method will convert any '&' symbols to the string
    "and", you should run any methods which convert HTML entities 
    (convert_html_entities and convert_misc_entities) before running
    this method.
    
    Based on Ruby's stringex package
    (http://github.com/rsl/stringex/tree/master)
    """
    s = re.sub(r'\.{3,}', " dot dot dot ", string)
    
    # Special rules for money
    money_replace = {
        r'(\s|^)\$(\d+)\.(\d+)(\s|\$)?': r'\2 dollars \3 cents',
        r'(\s|^)£(\d+)\.(\d+)(\s|\$)?': r'\2 pounds \3 pence',
    }
    for repl, subst in money_replace.items():
        s = re.sub(repl, r' %s ' % subst, s)
    
    # Back to normal rules
    repls =  {
        r'\s*&\s*': "and",
        r'\s*#': "number",
        r'\s*@\s*': "at",
        r'(\S|^)\.(\S)': r'\1 dot \2',
        r'(\s|^)\$(\d*)(\s|$)': r'\2 dollars',
        r'(\s|^)£(\d*)(\s|$)': r'\2 pounds',
        r'(\s|^)¥(\d*)(\s|$)': r'\2 yen',
        r'\s*\*\s*': "star",
        r'\s*%\s*': "percent",
        r'\s*(\\|\/)\s*': "slash",
    }
    for repl, subst in repls.items():
        s = re.sub(repl, r' %s ' % subst, s)
    s = re.sub(r"(^|\w)'(\w|$)", r'\1\2', s)
    return re.sub(r"[\.\,\:\;\(\)\[\]\/\?\!\^'\"_]", " ", s)
'''


def replace_whitespace(string, replace=" "):
    """Replace runs of whitespace in string
    
    Defaults to a single space but any replacement string may be
    specified as an argument. Examples::

        >>> replace_whitespace("Foo       bar")
        'Foo bar'
        >>> replace_whitespace("Foo       bar", "-")
        'Foo-bar'
    
    Based on Ruby's stringex package
    (http://github.com/rsl/stringex/tree/master)
    """
    return re.sub(r'\s+', replace, string)
 
def collapse(string, character=" "):
    """Removes specified character from the beginning and/or end of the
    string and then condenses runs of the character within the string.
    
    Based on Ruby's stringex package
    (http://github.com/rsl/stringex/tree/master)
    """
    reg = re.compile('(%s){2,}' % character)
    return re.sub(reg, character, string.strip(character))
