class TextFormat(object):

    def to_html(self, instr):
        raise NotImplementedError()


class MarkdownFormat(TextFormat):

    def to_html(self, instr):
        import markdown
        return markdown.markdown(instr)
