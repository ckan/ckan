import re
import webhelpers.markdown

class TextFormat(object):

    def to_html(self, instr):
        raise NotImplementedError()


class MarkdownFormat(TextFormat):
    internal_link = re.compile('(package|tag|group):([a-z0-9\-_]+)')
    normal_link = re.compile('<(http:[^>]+)>')
    
    def to_html(self, instr):
        if instr is None:
            return ''
        
        # Convert internal links
        instr = self.internal_link.sub(r'[\1:\2] (/\1/read/\2)', instr)

        # Convert <link> to markdown format
        instr = self.normal_link.sub(r'[\1] (\1)', instr)

        # Markdown to HTML
        return webhelpers.markdown.markdown(instr, safe_mode=True)

