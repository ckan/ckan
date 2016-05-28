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
Python 2, string literals by default have type ``str``. This has the risk of
accidentially introducing ASCII strings and makes a future support of Python 3
difficult (since string literals are interpreted as Unicode in Python 3).

Therefore, the ``unicode_literals`` feature is used to make Python 2 treat
string literals as Unicode::

    from __future__ import unicode_literals

This line should be the first code line in a Python file (after comments and
blank lines). See the documentation on `future statements`_ for details.

.. _future statements: https://docs.python.org/2/reference/simple_stmts.html#future

Once ``unicode_literals`` has been imported, any string literal in the module
will be converted to a ``unicode`` instance. However, some cases might require
a ``str`` literal (for example for a filename). This can be achieved using the
``b`` prefix (see `PEP 3112`_)::

    from __future__ import unicode_literals

    x = 'This is unicode'
    y = b'This is str'

.. _PEP 3112: https://www.python.org/dev/peps/pep-3112/


Best Practices
--------------

Use ``io.open`` to open text files
```````````````````````````````````
When opening text (not binary) files you should use `io.open`_ instead of
``open``. This allows you to specify the file's encoding and reads will return
``unicode`` instead of ``str``::

    import io

    with io.open('my_file.txt', 'r', encoding='utf-8') as f:
        text = f.read()  # contents is automatically decoded
                         # to unicode using UTF-8

.. _io.open: https://docs.python.org/2/library/io.html#io.open

Text files should be encoded using UTF-8 if possible.


Normalize strings before comparing them
```````````````````````````````````````
For many characters, Unicode offers descriptions. For example, a small latin
``e`` with an acute accent (``é``) can either be specified using its dedicated
code point (`U+00E9`_) or by combining the code points for ``e`` (`U+0065`_)
and the accent (`U+0301`_). Both variants will look the same but are different
from a numerical point of view::

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
    >>> x_norm = normalize('NFC', x)
    >>> y_norm = normalize('NFC', y)
    >>> print x_norm, y_norm
    é é
    >>> print repr(x_norm), repr(y_norm)
    u'\xe9' u'\xe9'
    >>> x_norm == y_norm
    True

.. _unicodedata.normalize: https://docs.python.org/2/library/unicodedata.html#unicodedata.normalize

