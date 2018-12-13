"""HTML/XHTML tag builder

HTML Builder provides: 

* an ``HTML`` object that creates (X)HTML tags in a Pythonic way.  

* a ``literal`` class used to mark strings containing intentional HTML markup. 

* a smart ``escape()`` function that preserves literals but
  escapes other strings that may accidentally contain markup characters ("<",
  ">", "&", '"', "'") or malicious Javascript tags.  Escaped strings are
  returned as literals to prevent them from being double-escaped later.

``literal`` is a subclass of ``unicode``, so it works with all string methods
and expressions.  The only thing special about it is the ``.__html__`` method,
which returns the string itself.  The ``escape()`` function follows a simple
protocol: if the object has an ``.__html__`` method, it calls that rather than
``.__str__`` to get the HTML representation.  Third-party libraries that do not
want to import ``literal`` (and this create a dependency on WebHelpers) can put
an ``.__html__`` method in their own classes returning the desired HTML
representation.

WebHelpers 1.2 uses MarkupSafe, a package which provides an enhanced
implementation of this protocol. Mako and Pylons have also switched to
MarkupSafe. Its advantages are a C speedup for escaping,
escaping single-quotes for security, and adding new methods to
``literal``. **literal** is now a subclass of ``markupsafe.Markup``.
**escape** is ``markupsafe.escape_silent``. (The latter does not exist yet in
MarkupSafe 0.9.3, but WebHelpers itself converts None to "" in the meantime). 

Single-quote escaping affects HTML attributes that are written like this:
*alt='Some text.'* rather than the normal *alt="Some text."*  If the text is a
replaceable parameter whose value contains a single quote, the browser would
think the value ends earlier than it does, thus enabling a potential cross-site
scripting (XSS) attack. WebHelpers 1.0 and earlier escaped double quotes but
not single quotes. MarkupSafe escapes both double and single quotes, preventing
this sort of attack.

MarkupSafe has some slight differences which should not cause compatibility
issues but may in the following edge cases.  (A) The ``force`` argument to
``escape()`` is gone. We doubt it was ever used. (B) The default encoding of
``literal()`` is "ascii" instead of "utf-8". (C) Double quotes are escaped as
"&#34;" instead of "&quot;". Single quotes are escaped as "&#39;". 

When ``literal`` is used in a mixed expression containing both literals and
ordinary strings, it tries hard to escape the strings and return a literal.
However, this depends on which value has "control" of the expression.
``literal`` seems to be able to take control with all combinations of the ``+``
operator, but with ``%`` and ``join`` it must be on the left side of the
expression.  So these all work::

    "A" + literal("B")
    literal(", ").join(["A", literal("B")])
    literal("%s %s") % (16, literal("kg"))

But these return an ordinary string which is prone to double-escaping later::

    "\\n".join([literal('<span class="foo">Foo!</span>'), literal('Bar!')])
    "%s %s" % (literal("16"), literal("&lt;em&gt;kg&lt;/em&gt;"))

Third-party libraries that don't want to import ``literal`` and thus avoid a
dependency on WebHelpers can add an ``.__html__`` method to any class, which
can return the same as ``.__str__`` or something else.  ``escape()`` trusts the
HTML method and does not escape the return value.  So only strings that lack
an ``.__html__`` method will be escaped.

The ``HTML`` object has the following methods for tag building:

``HTML(*strings)``
    Escape the string args, concatenate them, and return a literal.  This is
    the same as ``escape(s)`` but accepts multiple strings.  Multiple args are
    useful when mixing child tags with text, such as::

        html = HTML("The king is a >>", HTML.strong("fink"), "<<!")

``HTML.literal(*strings)``
    Same as ``literal`` but concatenates multiple arguments.

``HTML.comment(*strings)``
    Escape and concatenate the strings, and wrap the result in an HTML 
    comment.

``HTML.tag(tag, *content, **attrs)``
    Create an HTML tag ``tag`` with the keyword args converted to attributes.
    The other positional args become the content for the tag, and are escaped
    and concatenated.  If an attribute name conflicts with a Python keyword
    (notably "class"), append an underscore.  If an attribute value is
    ``None``, the attribute is not inserted.  Two special keyword args are
    recognized:
    
    ``c``
        Specifies the content.  This cannot be combined with content in
        positional args.  The purpose of this argument is to position the
        content at the end of the argument list to match the native HTML
        syntax more closely.  Its use is entirely optional.  The value can
        be a string, a tuple, or a tag.

    ``_closed``
        If present and false, do not close the tag.  Otherwise the tag will be
        closed with a closing tag or an XHTML-style trailing slash as described
        below.

    ``_nl``
        If present and true, insert a newline before the first content
        element, between each content element, and at the end of the tag.

    Example:

    >>> HTML.tag("a", href="http://www.yahoo.com", name=None, 
    ... c="Click Here")
    literal(u'<a href="http://www.yahoo.com">Click Here</a>')


``HTML.__getattr__``
    Same as ``HTML.tag`` but using attribute access.  Example:

    >>> HTML.a("Foo", href="http://example.com/", class_="important")
    literal(u'<a class="important" href="http://example.com/">Foo</a>')

``HTML.cdata``
    Wrap the text in a "<![CDATA[ ... ]]>" section. Plain strings will not be
    escaped because CDATA itself is an escaping syntax.

    >>> HTML.cdata(u"Foo")
    literal(u'<![CDATA[Foo]]>')

    >>> HTML.cdata(u"<p>")
    literal(u'<![CDATA[<p>]]>')

About XHTML and HTML
--------------------

This builder always produces tags that are valid as *both* HTML and XHTML.
"Void" tags -- those which can never have content like ``<br>`` and ``<input>``
-- are written like ``<br />``, with a space and a trailing ``/``.

*Only* void tags get this treatment.  The library will never, for
example, produce ``<script src="..." />``, which is invalid HTML.  Instead
it will produce ``<script src="..."></script>``.

The `W3C HTML validator <http://validator.w3.org/>`_ validates these
constructs as valid HTML Strict.  It does produce warnings, but those
warnings warn about the ambiguity if this same XML-style self-closing
tags are used for HTML elements that are allowed to take content (``<script>``,
``<textarea>``, etc).  This library never produces markup like that.

Rather than add options to generate different kinds of behavior, we
felt it was better to create markup that could be used in different
contexts without any real problems and without the overhead of passing
options around or maintaining different contexts, where you'd have to
keep track of whether markup is being rendered in an HTML or XHTML
context.

If you _really_ want tags without training slashes (e.g., ``<br>`)`, you can
abuse ``_closed=False`` to produce them.

"""
import re
from urllib import quote as url_escape
from UserDict import DictMixin

import markupsafe
try:
    from markupsafe import escape_silent as escape
except ImportError:
    def escape(s):
        if s is None:
            return EMPTY
        return markupsafe.escape(s)

class literal(markupsafe.Markup):
    """Represents an HTML literal.
    
    This subclass of unicode has a ``.__html__()`` method that is 
    detected by the ``escape()`` function.
    
    Also, if you add another string to this string, the other string 
    will be quoted and you will get back another literal object.  Also
    ``literal(...) % obj`` will quote any value(s) from ``obj``.  If
    you do something like ``literal(...) + literal(...)``, neither
    string will be changed because ``escape(literal(...))`` doesn't
    change the original literal.

    Changed in WebHelpers 1.2: the implementation is now now a subclass of
    ``markupsafe.Markup``.  This brings some new methods: ``.escape`` (class
    method), ``.unescape``, and ``.striptags``.
    
    """
    __slots__ = ()

    @classmethod
    def escape(cls, s):
        if s is None:
            return EMPTY
        return super(literal, cls).escape(s)


__all__ = ["HTML", "escape", "literal", "url_escape", "lit_sub"]

# Not included in __all__ because for specialized purposes only: 
# "format_attrs".

class UnfinishedTag(object):
    
    """Represents an unfinished or empty tag."""
    
    def __init__(self, tag):
        """Initialize with the tag name."""
        self._tag = tag

    def __call__(self, *args, **kw):
        """Create the tag with the arguments passed in."""
        return make_tag(self._tag, *args, **kw)

    def __str__(self):
        """Return a literal representation."""
        return literal('<%s />' % self._tag)

    def __html__(self):
        """Return the HTML escaped tag."""
        return str(self)


class UnfinishedComment(object):
    
    """Represents an unfinished or empty comment."""
    
    def __call__(self, *args):
        """Create the HTML comment."""
        return literal('<!--%s-->' % ''.join([str(x) for x in args]))
        
    def __html__(self):
        """Return the HTML escaped tag."""
        raise NotImplementedError(
            "You must call html.comment with some text")


class UnfinishedLiteral(object):
    
    """Represent an unfinished literal value."""
    
    def __call__(self, *args):
        """Return the literal HTML."""
        return literal(*args)

    def __html__(self):
        """Return the HTML escaped text."""
        raise NotImplementedError(
            "You must call html.literal with some text")


class HTMLBuilder(object):
    
    """Base HTML object."""
    
    comment = UnfinishedComment()
    literal = UnfinishedLiteral()
    
    def __getattr__(self, attr):
        """Generate the tag for the given attribute name."""
        if attr.startswith('_'):
            raise AttributeError
        result = self.__dict__[attr] = UnfinishedTag(attr.lower())
        return result

    def __call__(self, *args):
        """Join raw HTML and HTML escape it."""
        return literal(''.join([escape(x) for x in args]))

    def tag(self, tag, *args, **kw):
        return make_tag(tag, *args, **kw)

    def cdata(self, *content): 
        """Wrap the content in a "<![CDATA[ ... ]]>" section.

        The content will not be escaped because CDATA itself is an 
        escaping syntax.
        """
        # _CDATA_START and _CDATA_END are defined at end of module.
        parts = []
        parts.append(_CDATA_START)
        parts.extend(content)
        parts.append(_CDATA_END)
        s = "".join(parts)
        return literal(s)

def _attr_decode(v):
    """Parse out attributes that begin with '_'."""
    if v.endswith('_'):
        return v[:-1]
    else:
        return v


def make_tag(tag, *args, **kw):
    if kw.has_key("c"):
        assert not args, "The special 'c' keyword argument cannot be used "\
"in conjunction with non-keyword arguments"
        args = kw.pop("c")
    closed = kw.pop("_closed", True)
    nl = kw.pop("_nl", False)
    attrs_str = format_attrs(**kw)
    if not args and tag in empty_tags and closed:
        substr = '<%s%s />'
        html = literal(substr % (tag, attrs_str))
    else:
        chunks = ["<%s%s>" % (tag, attrs_str)]
        chunks.extend(escape(x) for x in args)
        if closed:
            chunks.append("</%s>" % tag)
        if nl:
            html = "\n".join(chunks)
        else:
            html = "".join(chunks)
    if nl:
        html += "\n"
    return literal(html)

def format_attrs(**attrs):
    """Format HTML attributes into a string of ' key="value"' pairs which
    can be inserted into an HTML tag.

    The attributes are sorted alphabetically.  If any value is None, the entire
    attribute is suppressed.

    Usage:
    >>> format_attrs(p=2, q=3)
    literal(u' p="2" q="3"')
    >>> format_attrs(p=2, q=None)
    literal(u' p="2"')
    >>> format_attrs(p=None)
    literal(u'')
    """
    strings = [u' %s="%s"' % (_attr_decode(attr), escape(value))
        for attr, value in sorted(attrs.iteritems())
        if value is not None]
    return literal("".join(strings))


def lit_sub(*args, **kw):
    """Literal-safe version of re.sub.  If the string to be operated on is
    a literal, return a literal result.  All arguments are passed directly to
    ``re.sub``.
    """
    lit = hasattr(args[2], '__html__')
    cls = args[2].__class__
    result = re.sub(*args, **kw)
    if lit:
        return cls(result)
    else:
        return result


empty_tags = set(["area", "base", "basefont", "br", "col", "frame", "hr",
    "img", "input", "isindex", "link", "meta", "param"])

HTML = HTMLBuilder()

# Constants depending on ``literal()`` and/or ``HTML``.
NL = literal(u"\n")
EMPTY = literal(u"")
BR = HTML.br(_nl=True)
_CDATA_START = literal(u"<![CDATA[") 
_CDATA_END = literal(u"]]>")
