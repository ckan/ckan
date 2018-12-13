"""Functions that convert from text markup languages to HTML and back.

"""
import re

from webhelpers.html import HTML, escape, literal, lit_sub
import webhelpers.textile as textile

# render() and sanitize() are imported from the private module 'render'.
from webhelpers.html.render import render, sanitize

__all__ = [
    "format_paragraphs",
    "markdown", 
    "nl2br",
    "render",
    "sanitize",
    "textilize",
    ]

_universal_newline_rx = re.compile(R"\r\n|\n|\r")  # All types of newline.
_paragraph_rx = re.compile(R"\n{2,}")  # Paragraph break: 2 or more newlines.
br = HTML.br() + "\n"

def markdown(text, markdown=None, **kwargs):
    """Format the text to HTML with Markdown formatting.

    Markdown is a wiki-like text markup language, originally written by
    John Gruber for Perl.  The helper converts Markdown text to HTML.

    There are at least two Python implementations of Markdown.
    Markdown <http://www.freewisdom.org/projects/python-markdown/>`_is the
    original port, and version 2.x contains extensions for footnotes, RSS, etc. 
    `Markdown2 <http://code.google.com/p/python-markdown2/>`_ is another port
    which claims to be faster and to handle edge cases better. 

    You can pass the desired Markdown module as the ``markdown``
    argument, or the helper will try to import ``markdown``. If neither is
    available, it will fall back to ``webhelpers.markdown``, which is
    Freewisdom's Markdown 1.7 without extensions.
    
    IMPORTANT:
    If your source text is untrusted and may contain malicious HTML markup,
    pass ``safe_mode="escape"`` to escape it, ``safe_mode="replace"`` to
    replace it with a scolding message, or ``safe_mode="remove"`` to strip it.
    """
    if not markdown:
        markdown = _get_markdown_module()
    return literal(markdown.markdown(text, **kwargs))

def _get_markdown_module():
    try:
        import markdown
    except ImportError:
        import webhelpers.markdown as markdown
    return markdown

def textilize(text, sanitize=False):
    """Format the text to HTML with Textile formatting.
    
    This function uses the `PyTextile library <http://dealmeida.net/>`_ 
    which is included with WebHelpers.
    
    Additionally, the output can be sanitized which will fix tags like 
    <img />,  <br /> and <hr /> for proper XHTML output.
    
    """
    texer = textile.Textiler(text)
    return literal(texer.process(sanitize=sanitize))

def nl2br(text):
    """Insert a <br /> before each newline.
    """
    if text is None:
        return literal("")
    text = lit_sub(_universal_newline_rx, "\n", text)
    text = HTML(text).replace("\n", br)
    return text

def format_paragraphs(text, preserve_lines=False):
    """Convert text to HTML paragraphs.

    ``text``:
        the text to convert.  Split into paragraphs at blank lines (i.e.,
        wherever two or more consecutive newlines appear), and wrap each
        paragraph in a <p>.

    ``preserve_lines``:
        If true, add <br />  before each single line break
    """
    if text is None:
        return literal("")
    text = lit_sub(_universal_newline_rx, "\n", text)
    paragraphs = _paragraph_rx.split(text)
    for i, para in enumerate(paragraphs):
        if preserve_lines:
            para = HTML(para)
            para = para.replace("\n", br)
        paragraphs[i] = HTML.p(para)
    return "\n\n".join(paragraphs)

