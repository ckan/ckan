from ckan.lib.helpers import paginate

class TextFormat(object):

    def to_html(self, instr):
        raise NotImplementedError()


class MarkdownFormat(TextFormat):

    def to_html(self, instr):
        if instr is None:
            return ''
        # import markdown
        import webhelpers.markdown
        return webhelpers.markdown.markdown(instr)

