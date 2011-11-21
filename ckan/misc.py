import re
import logging
import urllib
import webhelpers.markdown

from pylons.i18n import _

log = logging.getLogger(__name__)

class TextFormat(object):

    def to_html(self, instr):
        raise NotImplementedError()


class MarkdownFormat(TextFormat):
    internal_link = re.compile('(dataset|package|group):([a-z0-9\-_]+)')

    # tag names are allowed more characters, including spaces.  So are
    # treated specially.
    internal_tag_link = re.compile(\
        r"""(tag):                               # group 1
            (                                    # capture name (inc. quotes) (group 2)
            (")?                                 # optional quotes for multi-word name (group 3)
            (                                    # begin capture of the name w/o quotes (group 4)
            (?(3)                                # if the quotes matched in group 3
                [ \w\-.]                         #     then capture spaces (as well as other things)
                |                                # else
                [\w\-.]                          #     don't capture spaces
            )                                    # end
            +)                                   # end capture of the name w/o quotes (group 4)
            (?(3)")                              # close opening quote if necessary
            )                                    # end capture of the name with quotes (group 2)
        """, re.VERBOSE|re.UNICODE)
    normal_link = re.compile('<(http:[^>]+)>')

    html_whitelist = 'b center li ol p table td tr ul'.split(' ')
    whitelist_elem = re.compile(r'<(\/?(%s)[^>]*)>' % "|".join(html_whitelist), re.IGNORECASE)
    whitelist_escp = re.compile(r'\\xfc\\xfd(\/?(%s)[^>]*?)\\xfd\\xfc' % "|".join(html_whitelist), re.IGNORECASE)
    normal_link = re.compile(r'<a[^>]*?href="([^"]*?)"[^>]*?>', re.IGNORECASE)
    abbrev_link = re.compile(r'<(http://[^>]*)>', re.IGNORECASE)
    any_link = re.compile(r'<a[^>]*?>', re.IGNORECASE)
    close_link = re.compile(r'<(\/a[^>]*)>', re.IGNORECASE)
    link_escp = re.compile(r'\\xfc\\xfd(\/?(%s)[^>]*?)\\xfd\\xfc' % "|".join(['a']), re.IGNORECASE)
    web_address = re.compile(r'(\s|<p>)((http|https):\/\/[\w\-_]+(\.[\w\-_]+)+([\w\-\.,@?^=%&amp;:/~\+#]*[\w\-\@?^=%&amp;/~\+#])?)', re.IGNORECASE)
    
    def to_html(self, text):
        if text is None:
            return ''
        # Encode whitelist elements.
        text = self.whitelist_elem.sub(r'\\\\xfc\\\\xfd\1\\\\xfd\\\\xfc', text)

        # Encode links only in an acceptable format (guard against spammers)
        text = self.normal_link.sub(r'\\\\xfc\\\\xfda href="\1" target="_blank" rel="nofollow"\\\\xfd\\\\xfc', text)
        text = self.abbrev_link.sub(r'\\\\xfc\\\\xfda href="\1" target="_blank" rel="nofollow"\\\\xfd\\\\xfc\1</a>', text)
        text = self.any_link.sub(r'\\\\xfc\\\\xfda href="TAG MALFORMED" target="_blank" rel="nofollow"\\\\xfd\\\\xfc', text)
        text = self.close_link.sub(r'\\\\xfc\\\\xfd\1\\\\xfd\\\\xfc', text)

        # Convert internal tag links
        text = self.internal_tag_link.sub(self._create_tag_link, text)

        # Convert internal links.
        text = self.internal_link.sub(r'[\1:\2] (/\1/\2)', text)

        # Convert <link> to markdown format.
        text = self.normal_link.sub(r'[\1] (\1)', text)

        # Convert <link> to markdown format.
        text = self.normal_link.sub(r'[\1] (\1)', text)

        # Markdown to HTML.
        text = webhelpers.markdown.markdown(text, safe_mode=True)

        # Remaining unlinked web addresses to become addresses
        text = self.web_address.sub(r'\1<a href="\2" target="_blank" rel="nofollow">\2</a>', text)

        # Decode whitelist elements.
        text = self.whitelist_escp.sub(r'<\1>', text)
        text = self.link_escp.sub(r'<\1>', text)

        return text

    def _create_tag_link(self, match_object):
        """
        A callback used to create the internal tag link.

        The reason for this is that webhelpers.markdown does not percent-escape
        spaces, nor does it encode unicode characters correctly.

        This is only applied to the tag substitution since only tags may
        have spaces or unicode characters.
        """
        g = match_object.group
        url = urllib.quote(g(4).encode('utf8'))
        return r'[%s:%s] (/%s/%s)' % (g(1), g(2), g(1), url)
