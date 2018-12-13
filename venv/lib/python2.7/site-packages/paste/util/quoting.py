# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

import cgi
import htmlentitydefs
import urllib
import re

__all__ = ['html_quote', 'html_unquote', 'url_quote', 'url_unquote',
           'strip_html']

default_encoding = 'UTF-8'

def html_quote(v, encoding=None):
    r"""
    Quote the value (turned to a string) as HTML.  This quotes <, >,
    and quotes:

    >>> html_quote(1)
    '1'
    >>> html_quote(None)
    ''
    >>> html_quote('<hey!>')
    '&lt;hey!&gt;'
    >>> html_quote(u'\u1029')
    '\xe1\x80\xa9'
    """
    encoding = encoding or default_encoding
    if v is None:
        return ''
    elif isinstance(v, str):
        return cgi.escape(v, 1)
    elif isinstance(v, unicode):
        return cgi.escape(v.encode(encoding), 1)
    else:
        return cgi.escape(unicode(v).encode(encoding), 1)

_unquote_re = re.compile(r'&([a-zA-Z]+);')
def _entity_subber(match, name2c=htmlentitydefs.name2codepoint):
    code = name2c.get(match.group(1))
    if code:
        return unichr(code)
    else:
        return match.group(0)

def html_unquote(s, encoding=None):
    r"""
    Decode the value.

    >>> html_unquote('&lt;hey&nbsp;you&gt;')
    u'<hey\xa0you>'
    >>> html_unquote('')
    u''
    >>> html_unquote('&blahblah;')
    u'&blahblah;'
    >>> html_unquote('\xe1\x80\xa9')
    u'\u1029'
    """
    if isinstance(s, str):
        if s == '':
            # workaround re.sub('', '', u'') returning '' < 2.5.2
            # instead of u'' >= 2.5.2
            return u''
        s = s.decode(encoding or default_encoding)
    return _unquote_re.sub(_entity_subber, s)

def strip_html(s):
    # should this use html_unquote?
    s = re.sub('<.*?>', '', s)
    s = html_unquote(s)
    return s

def no_quote(s):
    """
    Quoting that doesn't do anything
    """
    return s

_comment_quote_re = re.compile(r'\-\s*\>')
# Everything but \r, \n, \t:
_bad_chars_re = re.compile('[\x00-\x08\x0b-\x0c\x0e-\x1f]')
def comment_quote(s):
    """
    Quote that makes sure text can't escape a comment
    """
    comment = str(s)
    #comment = _bad_chars_re.sub('', comment)
    #print 'in ', repr(str(s))
    #print 'out', repr(comment)
    comment = _comment_quote_re.sub('-&gt;', comment)
    return comment

url_quote = urllib.quote
url_unquote = urllib.unquote

if __name__ == '__main__':
    import doctest
    doctest.testmod()
