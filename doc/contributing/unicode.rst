================
Unicode handling
================
This document explains how Unicode and related issues are handled in CKAN.
For a general introduction to Unicode and Unicode handling in Python 2 please
read the `Python 2 Unicode HOWTO`_. Since Unicode handling differs greatly
between Python 2 and Python 3 you might also be interested in the
`Python 3 Unicode HOWTO`_.

.. _Python 2 Unicode HOWTO: https://docs.python.org/2/howto/unicode.html
.. _Python 3 Unicode HOWTO: https://docs.python.org/3/howto/unicode.html

.. note::

    This document describes the intended future state of Unicode handling in
    CKAN. For historic reasons, some existing code does not yet follow the
    rules described here.

    *New code should always comply with the rules in this document. Exceptions
    must be documented.*


Overall Strategy
----------------
CKAN only uses Unicode internally (``unicode`` on Python 2). Conversion to/from
ASCII strings happens on the boundary to other systems/libaries if necessary.


Encoding of Python files
------------------------
Files containing Python source code (``*.py``) must be encoded using UTF-8, and
the encoding must be declared using the following header::

    # encoding: utf-8

This line must be the first or second line in the file. See `PEP 263`_ for
details.

.. _PEP 263: https://www.python.org/dev/peps/pep-0263/


String literals
---------------
String literals are string values given directly in the source code (as opposed
to strings variables read from a file, received via argument, etc.). In
Python 2, string literals by default have type ``str``. They can be changed to
``unicode`` by adding a ``u`` prefix. In addition, the ``b`` prefix can be used
to explicitly mark a literal as ``str``::

    x = "I'm a str literal"
    y = u"I'm a unicode literal"
    z = b"I'm also a str literal"

In CKAN, every string literal must carry either a ``u`` or a ``b`` prefix.
While the latter is redundant in Python 2, it makes the developer's intention
explicit and eases a future migration to Python 3.

This rule also holds for *raw strings*, which are created using an ``r``
prefix. Simply use ``ur`` instead::

    m = re.match(ur'A\s+Unicode\s+pattern')

For more information on string prefixes please refer to the
`Python documentation`_.

.. _Python documentation: https://docs.python.org/2.7/reference/lexical_analysis.html#string-literals

.. note::

    The ``unicode_literals`` `future statement`_ is *not* used in CKAN.

.. _future statement: https://docs.python.org/2/reference/simple_stmts.html#future


Best Practices
--------------

Use ``io.open`` to open text files
```````````````````````````````````
When opening text (not binary) files you should use `io.open`_ instead of
``open``. This allows you to specify the file's encoding and reads will return
``unicode`` instead of ``str``::

    import io

    with io.open(b'my_file.txt', u'r', encoding=u'utf-8') as f:
        text = f.read()  # contents is automatically decoded
                         # to unicode using UTF-8

.. _io.open: https://docs.python.org/2/library/io.html#io.open

Text files should be encoded using UTF-8 if possible.


Normalize strings before comparing them
```````````````````````````````````````
For many characters, Unicode offers multiple descriptions. For example, a small
latin ``e`` with an acute accent (``é``) can either be specified using its
dedicated code point (`U+00E9`_) or by combining the code points for ``e``
(`U+0065`_) and the accent (`U+0301`_). Both variants will look the same but
are different from a numerical point of view::

    >>> x = u'\N{LATIN SMALL LETTER E WITH ACUTE}'
    >>> y = u'\N{LATIN SMALL LETTER E}\N{COMBINING ACUTE ACCENT}'
    >>> print x, y
    é é
    >>> print repr(x), repr(y)
    u'\xe9' u'e\u0301'
    >>> x == y
    False

.. _U+00E9: http://www.fileformat.info/info/unicode/char/e9
.. _U+0065: http://www.fileformat.info/info/unicode/char/0065
.. _U+0301: http://www.fileformat.info/info/unicode/char/0301

Therefore, if you want to compare two Unicode strings based on their characters
you need to normalize them first using `unicodedata.normalize`_::

    >>> from unicodedata import normalize
    >>> x_norm = normalize(u'NFC', x)
    >>> y_norm = normalize(u'NFC', y)
    >>> print x_norm, y_norm
    é é
    >>> print repr(x_norm), repr(y_norm)
    u'\xe9' u'\xe9'
    >>> x_norm == y_norm
    True

.. _unicodedata.normalize: https://docs.python.org/2/library/unicodedata.html#unicodedata.normalize


Use the Unicode flag in regular expressions
```````````````````````````````````````````
By default, the character classes of Python's `re`_ module (``\w``, ``\d``,
...) only match ASCII-characters. For example, ``\w`` (alphanumeric character)
does, by default, not match ``ö``::

    >>> print re.match(ur'^\w$', u'ö')
    None

Therefore, you need to explicitly activate Unicode mode by passing the `re.U`_
flag::

    >>> print re.match(ur'^\w$', u'ö', re.U)
    <_sre.SRE_Match object at 0xb60ea2f8>

The type of the values returned by ``re.split``, ``re.MatchObject.group``, etc.
depends on the type of the input string::

    >>> re.split(ur'\W+', b'Just a string!', flags=re.U)
    ['Just', 'a', 'string', '']

    >>> re.split(ur'\W+', u'Just some Unicode!', flags=re.U)
    [u'Just', u'some', u'Unicode', u'']

Note that the type of the *pattern string* does not influence the return type.

.. _re: https://docs.python.org/2/library/re.html
.. _re.U: https://docs.python.org/2/library/re.html#re.U

