import re
import logging
import webhelpers.markdown

from pylons.i18n import _

log = logging.getLogger(__name__)

class TextFormat(object):

    def to_html(self, instr):
        raise NotImplementedError()


class MarkdownFormat(TextFormat):
    internal_link = re.compile('(dataset|package|tag|group):([a-z0-9\-_]+)')
    normal_link = re.compile('<(http:[^>]+)>')

    html_whitelist = 'b center li ol p table td tr ul'.split(' ')
    whitelist_elem = re.compile(r'<(\/?(%s)[^>]*)>' % "|".join(html_whitelist), re.IGNORECASE)
    whitelist_escp = re.compile(r'\\xfc\\xfd(\/?(%s)[^>]*?)\\xfd\\xfc' % "|".join(html_whitelist), re.IGNORECASE)
    normal_link = re.compile(r'<a[^>]*?href="([^"]*?)"[^>]*?>', re.IGNORECASE)
    abbrev_link = re.compile(r'<(http://[^>]*)>', re.IGNORECASE)
    any_link = re.compile(r'<a[^>]*?>', re.IGNORECASE)
    close_link = re.compile(r'<(\/a[^>]*)>', re.IGNORECASE)
    link_escp = re.compile(r'\\xfc\\xfd(\/?(%s)[^>]*?)\\xfd\\xfc' % "|".join(['a']), re.IGNORECASE)
    web_address = re.compile(r'(\s|^)((http|https):\/\/[\w\-_]+(\.[\w\-_]+)+([\w\-\.,@?^=%&amp;:/~\+#]*[\w\-\@?^=%&amp;/~\+#])?)', re.IGNORECASE)
    
    def to_html(self, text):
        if text is None:
            return ''
        # Encode whitelist elements.
        text = self.whitelist_elem.sub(r'\\\\xfc\\\\xfd\1\\\\xfd\\\\xfc', text)

        # Discover external addresses and make them links
        text = self.web_address.sub(r'\1<\2>', text)
        
        # Encode links only in an acceptable format (guard against spammers)
        text = self.normal_link.sub(r'\\\\xfc\\\\xfda href="\1" target="_blank" rel="nofollow"\\\\xfd\\\\xfc', text)
        text = self.abbrev_link.sub(r'\\\\xfc\\\\xfda href="\1" target="_blank" rel="nofollow"\\\\xfd\\\\xfc\1</a>', text)
        text = self.any_link.sub(r'\\\\xfc\\\\xfda href="TAG MALFORMED" target="_blank" rel="nofollow"\\\\xfd\\\\xfc', text)
        text = self.close_link.sub(r'\\\\xfc\\\\xfd\1\\\\xfd\\\\xfc', text)

        # Convert internal links.
        text = self.internal_link.sub(r'[\1:\2] (/\1/\2)', text)

        # Convert <link> to markdown format.
        text = self.normal_link.sub(r'[\1] (\1)', text)

        # Convert <link> to markdown format.
        text = self.normal_link.sub(r'[\1] (\1)', text)

        # Markdown to HTML.
        text = webhelpers.markdown.markdown(text, safe_mode=True)

        # Decode whitelist elements.
        text = self.whitelist_escp.sub(r'<\1>', text)
        text = self.link_escp.sub(r'<\1>', text)

        return text
