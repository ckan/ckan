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

CKAN uses the `six`_ module to provide simultaneous compatibility with
Python 2 and Python 3.  All **strs** are Unicode in Python 3 so the builtins
``unicode`` and ``basestring`` have been removed so there are a few general
rules to follow:

.. _six: http://six.readthedocs.io

#. Change all calls to ``basestring()`` into calls to ``six.string_types()``
#. Change remaining instances of ``basestring`` to ``six.string_types``
#. Change all instances of ``(str, unicode)`` to ``six.string_types``
#. Change all calls to ``unicode()`` into calls to ``six.text_type()``
#. Change remaining instances of ``unicode`` to ``six.text_type``

These rules do not apply in every instance so some thought needs to be
given about the context around these changes.

.. note::

    This document describes the intended future state of Unicode handling in
    CKAN. For historic reasons, some existing code does not yet follow the
    rules described here.

    *New code should always comply with the rules in this document. Exceptions
    must be documented.*


Overall Strategy
----------------
CKAN only uses Unicode internally (``six.text_type`` on both Python 2 and
Python 3). Conversion to/from ASCII strings happens on the boundary to other
systems/libraries if necessary.


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

In Python 3, all ``str`` are Unicode and ``str`` and ``bytes`` are explicitly
different data types so::

    x = "I'm a str literal"
    y = u"I'm also a str literal"
    z = b"I'm a bytes literal"

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
Unicode instead of ASCII::

    import io

    with io.open(u'my_file.txt', u'r', encoding=u'utf-8') as f:
        text = f.read()  # contents is automatically decoded
                         # to Unicode using UTF-8

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

.. note::

    Some functions (e.g. ``re.split`` and ``re.sub``) take additional optional
    parameters before the flags, so you should pass the flag via a keyword
    argument::

        replaced = re.sub(ur'\W', u'_', original, flags=re.U)

The type of the values returned by ``re.split``, ``re.MatchObject.group``, etc.
depends on the type of the input string::

    >>> re.split(ur'\W+', b'Just a string!', flags=re.U)
    ['Just', 'a', 'string', '']

    >>> re.split(ur'\W+', u'Just some Unicode!', flags=re.U)
    [u'Just', u'some', u'Unicode', u'']

Note that the type of the *pattern string* does not influence the return type.

.. _re: https://docs.python.org/2/library/re.html
.. _re.U: https://docs.python.org/2/library/re.html#re.U


Filenames
`````````
Like all other strings, filenames should be stored as Unicode strings
internally. However, some filesystem operations return or expect byte strings,
so filenames have to be encoded/decoded appropriately. Unfortunately, different
operating systems use different encodings for their filenames, and on some of
them (e.g. Linux) the file system encoding is even configurable by the user.

To make decoding and encoding of filenames easier, the ``ckan.lib.io`` module
therefore contains the functions ``decode_path`` and ``encode_path``, which
automatically use the correct encoding::

    import io
    import json

    from ckan.lib.io import decode_path

    # __file__ is a byte string, so we decode it
    MODULE_FILE = decode_path(__file__)
    print(u'Running from ' + MODULE_FILE)

    # The functions in os.path return unicode if given unicode
    MODULE_DIR = os.path.dirname(MODULE_FILE)
    DATA_FILE = os.path.join(MODULE_DIR, u'data.json')

    # Most of Python's built-in I/O-functions accept Unicode filenames as input
    # and encode them automatically
    with io.open(DATA_FILE, encoding='utf-8') as f:
        data = json.load(f)

Note that almost all Python's built-in I/O-functions accept Unicode filenames
as input and encode them automatically, so using ``encode_path`` is usually not
necessary.

The return type of some of Python's I/O-functions (e.g. os.listdir_ and
os.walk_) depends on the type of their input: If passed byte strings they
return byte strings and if passed Unicode they automatically decode the raw
filenames to Unicode before returning them. Other functions exist in two
variants that return byte strings (e.g. os.getcwd_) and Unicode (os.getcwdu_),
respectively.

.. warning::

    Some of Python's I/O-functions may return *both* byte and Unicode strings
    for *a single* call. For example, os.listdir_ will normally return Unicode
    when passed Unicode, but filenames that cannot be decoded using the
    filesystem encoding will still be returned as byte strings!

    Note that if the filename of an existing file cannot be decoded using the
    filesystem's encoding then the environment Python is running in is most
    probably incorrectly set up.

The instructions above are meant for the names of existing files that are
obtained using Python's I/O functions. However, sometimes one also wants to
create new files whose names are generated from unknown sources (e.g. user
input). To make sure that the generated filename is safe to use and can be
represented using the filesystem's encoding use
``ckan.lib.munge.munge_filename``::

    >> ckan.lib.munge.munge_filename(u'Data from Linköping (year: 2016).txt')
    u'data-from-linkoping-year-2016.txt'

.. note::

    ``munge_filename`` will remove a leading path from the filename.

.. _os.listdir: https://docs.python.org/2/library/os.html#os.listdir
.. _os.walk: https://docs.python.org/2/library/os.html#os.walk
.. _os.getcwd: https://docs.python.org/2/library/os.html#os.getcwd
.. _os.getcwdu: https://docs.python.org/2/library/os.html#os.getcwdu
