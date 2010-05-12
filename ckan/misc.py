import re
import webhelpers.markdown

class TextFormat(object):

    def to_html(self, instr):
        raise NotImplementedError()


class MarkdownFormat(TextFormat):
    internal_link = re.compile('(package|tag|group):([a-z0-9\-_]+)')
    normal_link = re.compile('<(http:[^>]+)>')

    html_whitelist = 'a b center li ol p table td tr ul'.split(' ')
    whitelist_elem = re.compile(r'<(\/?(%s)[^>]*)>' % "|".join(html_whitelist), re.IGNORECASE)
    whitelist_escp = re.compile(r'\\xfc\\xfd(\/?(%s)[^>]*?)\\xfd\\xfc' % "|".join(html_whitelist), re.IGNORECASE)
    
    def to_html(self, text):
        if text is None:
            return ''
        
        # Encode whitelist elements.
        text = self.whitelist_elem.sub(r'\\\\xfc\\\\xfd\1\\\\xfd\\\\xfc', text)

        # Convert internal links.
        text = self.internal_link.sub(r'[\1:\2] (/\1/read/\2)', text)

        # Convert <link> to markdown format.
        text = self.normal_link.sub(r'[\1] (\1)', text)

        # Convert <link> to markdown format.
        text = self.normal_link.sub(r'[\1] (\1)', text)

        # Markdown to HTML.
        text = webhelpers.markdown.markdown(text, safe_mode=True)

        # Decode whitelist elements.
        text = self.whitelist_escp.sub(r'<\1>', text)

        return text

