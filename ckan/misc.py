class TextFormat(object):

    def to_html(self, instr):
        raise NotImplementedError()


class MarkdownFormat(TextFormat):

    def to_html(self, instr):
        if instr is None:
            return ''
        import markdown
        return markdown.markdown(instr)
