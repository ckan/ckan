from ckan.misc import MarkdownFormat

class TestFormatText:

    def test_markdown(self):
        instr = '''# Hello World

**Some bolded text.**

*Some italicized text.*
'''
        exp = '''

<h1>Hello World</h1>
<p><strong>Some bolded text.</strong>
</p>
<p><em>Some italicized text.</em>
</p>

'''
        format = MarkdownFormat()
        out = format.to_html(instr)
        assert out == exp
